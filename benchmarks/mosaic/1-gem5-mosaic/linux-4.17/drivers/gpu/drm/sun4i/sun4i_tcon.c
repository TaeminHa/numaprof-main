/*
 * Copyright (C) 2015 Free Electrons
 * Copyright (C) 2015 NextThing Co
 *
 * Maxime Ripard <maxime.ripard@free-electrons.com>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of
 * the License, or (at your option) any later version.
 */

#include <drm/drmP.h>
#include <drm/drm_atomic_helper.h>
#include <drm/drm_crtc.h>
#include <drm/drm_crtc_helper.h>
#include <drm/drm_encoder.h>
#include <drm/drm_modes.h>
#include <drm/drm_of.h>
#include <drm/drm_panel.h>

#include <uapi/drm/drm_mode.h>

#include <linux/component.h>
#include <linux/ioport.h>
#include <linux/of_address.h>
#include <linux/of_device.h>
#include <linux/of_irq.h>
#include <linux/regmap.h>
#include <linux/reset.h>

#include "sun4i_crtc.h"
#include "sun4i_dotclock.h"
#include "sun4i_drv.h"
#include "sun4i_lvds.h"
#include "sun4i_rgb.h"
#include "sun4i_tcon.h"
#include "sunxi_engine.h"

static struct drm_connector *sun4i_tcon_get_connector(const struct drm_encoder *encoder)
{
	struct drm_connector *connector;
	struct drm_connector_list_iter iter;

	drm_connector_list_iter_begin(encoder->dev, &iter);
	drm_for_each_connector_iter(connector, &iter)
		if (connector->encoder == encoder) {
			drm_connector_list_iter_end(&iter);
			return connector;
		}
	drm_connector_list_iter_end(&iter);

	return NULL;
}

static int sun4i_tcon_get_pixel_depth(const struct drm_encoder *encoder)
{
	struct drm_connector *connector;
	struct drm_display_info *info;

	connector = sun4i_tcon_get_connector(encoder);
	if (!connector)
		return -EINVAL;

	info = &connector->display_info;
	if (info->num_bus_formats != 1)
		return -EINVAL;

	switch (info->bus_formats[0]) {
	case MEDIA_BUS_FMT_RGB666_1X7X3_SPWG:
		return 18;

	case MEDIA_BUS_FMT_RGB888_1X7X4_JEIDA:
	case MEDIA_BUS_FMT_RGB888_1X7X4_SPWG:
		return 24;
	}

	return -EINVAL;
}

static void sun4i_tcon_channel_set_status(struct sun4i_tcon *tcon, int channel,
					  bool enabled)
{
	struct clk *clk;

	switch (channel) {
	case 0:
		WARN_ON(!tcon->quirks->has_channel_0);
		regmap_update_bits(tcon->regs, SUN4I_TCON0_CTL_REG,
				   SUN4I_TCON0_CTL_TCON_ENABLE,
				   enabled ? SUN4I_TCON0_CTL_TCON_ENABLE : 0);
		clk = tcon->dclk;
		break;
	case 1:
		WARN_ON(!tcon->quirks->has_channel_1);
		regmap_update_bits(tcon->regs, SUN4I_TCON1_CTL_REG,
				   SUN4I_TCON1_CTL_TCON_ENABLE,
				   enabled ? SUN4I_TCON1_CTL_TCON_ENABLE : 0);
		clk = tcon->sclk1;
		break;
	default:
		DRM_WARN("Unknown channel... doing nothing\n");
		return;
	}

	if (enabled) {
		clk_prepare_enable(clk);
		clk_rate_exclusive_get(clk);
	} else {
		clk_rate_exclusive_put(clk);
		clk_disable_unprepare(clk);
	}
}

static void sun4i_tcon_lvds_set_status(struct sun4i_tcon *tcon,
				       const struct drm_encoder *encoder,
				       bool enabled)
{
	if (enabled) {
		u8 val;

		regmap_update_bits(tcon->regs, SUN4I_TCON0_LVDS_IF_REG,
				   SUN4I_TCON0_LVDS_IF_EN,
				   SUN4I_TCON0_LVDS_IF_EN);

		/*
		 * As their name suggest, these values only apply to the A31
		 * and later SoCs. We'll have to rework this when merging
		 * support for the older SoCs.
		 */
		regmap_write(tcon->regs, SUN4I_TCON0_LVDS_ANA0_REG,
			     SUN6I_TCON0_LVDS_ANA0_C(2) |
			     SUN6I_TCON0_LVDS_ANA0_V(3) |
			     SUN6I_TCON0_LVDS_ANA0_PD(2) |
			     SUN6I_TCON0_LVDS_ANA0_EN_LDO);
		udelay(2);

		regmap_update_bits(tcon->regs, SUN4I_TCON0_LVDS_ANA0_REG,
				   SUN6I_TCON0_LVDS_ANA0_EN_MB,
				   SUN6I_TCON0_LVDS_ANA0_EN_MB);
		udelay(2);

		regmap_update_bits(tcon->regs, SUN4I_TCON0_LVDS_ANA0_REG,
				   SUN6I_TCON0_LVDS_ANA0_EN_DRVC,
				   SUN6I_TCON0_LVDS_ANA0_EN_DRVC);

		if (sun4i_tcon_get_pixel_depth(encoder) == 18)
			val = 7;
		else
			val = 0xf;

		regmap_write_bits(tcon->regs, SUN4I_TCON0_LVDS_ANA0_REG,
				  SUN6I_TCON0_LVDS_ANA0_EN_DRVD(0xf),
				  SUN6I_TCON0_LVDS_ANA0_EN_DRVD(val));
	} else {
		regmap_update_bits(tcon->regs, SUN4I_TCON0_LVDS_IF_REG,
				   SUN4I_TCON0_LVDS_IF_EN, 0);
	}
}

void sun4i_tcon_set_status(struct sun4i_tcon *tcon,
			   const struct drm_encoder *encoder,
			   bool enabled)
{
	bool is_lvds = false;
	int channel;

	switch (encoder->encoder_type) {
	case DRM_MODE_ENCODER_LVDS:
		is_lvds = true;
		/* Fallthrough */
	case DRM_MODE_ENCODER_NONE:
		channel = 0;
		break;
	case DRM_MODE_ENCODER_TMDS:
	case DRM_MODE_ENCODER_TVDAC:
		channel = 1;
		break;
	default:
		DRM_DEBUG_DRIVER("Unknown encoder type, doing nothing...\n");
		return;
	}

	if (is_lvds && !enabled)
		sun4i_tcon_lvds_set_status(tcon, encoder, false);

	regmap_update_bits(tcon->regs, SUN4I_TCON_GCTL_REG,
			   SUN4I_TCON_GCTL_TCON_ENABLE,
			   enabled ? SUN4I_TCON_GCTL_TCON_ENABLE : 0);

	if (is_lvds && enabled)
		sun4i_tcon_lvds_set_status(tcon, encoder, true);

	sun4i_tcon_channel_set_status(tcon, channel, enabled);
}

void sun4i_tcon_enable_vblank(struct sun4i_tcon *tcon, bool enable)
{
	u32 mask, val = 0;

	DRM_DEBUG_DRIVER("%sabling VBLANK interrupt\n", enable ? "En" : "Dis");

	mask = SUN4I_TCON_GINT0_VBLANK_ENABLE(0) |
	       SUN4I_TCON_GINT0_VBLANK_ENABLE(1);

	if (enable)
		val = mask;

	regmap_update_bits(tcon->regs, SUN4I_TCON_GINT0_REG, mask, val);
}
EXPORT_SYMBOL(sun4i_tcon_enable_vblank);

/*
 * This function is a helper for TCON output muxing. The TCON output
 * muxing control register in earlier SoCs (without the TCON TOP block)
 * are located in TCON0. This helper returns a pointer to TCON0's
 * sun4i_tcon structure, or NULL if not found.
 */
static struct sun4i_tcon *sun4i_get_tcon0(struct drm_device *drm)
{
	struct sun4i_drv *drv = drm->dev_private;
	struct sun4i_tcon *tcon;

	list_for_each_entry(tcon, &drv->tcon_list, list)
		if (tcon->id == 0)
			return tcon;

	dev_warn(drm->dev,
		 "TCON0 not found, display output muxing may not work\n");

	return NULL;
}

void sun4i_tcon_set_mux(struct sun4i_tcon *tcon, int channel,
			const struct drm_encoder *encoder)
{
	int ret = -ENOTSUPP;

	if (tcon->quirks->set_mux)
		ret = tcon->quirks->set_mux(tcon, encoder);

	DRM_DEBUG_DRIVER("Muxing encoder %s to CRTC %s: %d\n",
			 encoder->name, encoder->crtc->name, ret);
}

static int sun4i_tcon_get_clk_delay(const struct drm_display_mode *mode,
				    int channel)
{
	int delay = mode->vtotal - mode->vdisplay;

	if (mode->flags & DRM_MODE_FLAG_INTERLACE)
		delay /= 2;

	if (channel == 1)
		delay -= 2;

	delay = min(delay, 30);

	DRM_DEBUG_DRIVER("TCON %d clock delay %u\n", channel, delay);

	return delay;
}

static void sun4i_tcon0_mode_set_common(struct sun4i_tcon *tcon,
					const struct drm_display_mode *mode)
{
	/* Configure the dot clock */
	clk_set_rate(tcon->dclk, mode->crtc_clock * 1000);

	/* Set the resolution */
	regmap_write(tcon->regs, SUN4I_TCON0_BASIC0_REG,
		     SUN4I_TCON0_BASIC0_X(mode->crtc_hdisplay) |
		     SUN4I_TCON0_BASIC0_Y(mode->crtc_vdisplay));
}

static void sun4i_tcon0_mode_set_lvds(struct sun4i_tcon *tcon,
				      const struct drm_encoder *encoder,
				      const struct drm_display_mode *mode)
{
	unsigned int bp;
	u8 clk_delay;
	u32 reg, val = 0;

	WARN_ON(!tcon->quirks->has_channel_0);

	tcon->dclk_min_div = 7;
	tcon->dclk_max_div = 7;
	sun4i_tcon0_mode_set_common(tcon, mode);

	/* Adjust clock delay */
	clk_delay = sun4i_tcon_get_clk_delay(mode, 0);
	regmap_update_bits(tcon->regs, SUN4I_TCON0_CTL_REG,
			   SUN4I_TCON0_CTL_CLK_DELAY_MASK,
			   SUN4I_TCON0_CTL_CLK_DELAY(clk_delay));

	/*
	 * This is called a backporch in the register documentation,
	 * but it really is the back porch + hsync
	 */
	bp = mode->crtc_htotal - mode->crtc_hsync_start;
	DRM_DEBUG_DRIVER("Setting horizontal total %d, backporch %d\n",
			 mode->crtc_htotal, bp);

	/* Set horizontal display timings */
	regmap_write(tcon->regs, SUN4I_TCON0_BASIC1_REG,
		     SUN4I_TCON0_BASIC1_H_TOTAL(mode->htotal) |
		     SUN4I_TCON0_BASIC1_H_BACKPORCH(bp));

	/*
	 * This is called a backporch in the register documentation,
	 * but it really is the back porch + hsync
	 */
	bp = mode->crtc_vtotal - mode->crtc_vsync_start;
	DRM_DEBUG_DRIVER("Setting vertical total %d, backporch %d\n",
			 mode->crtc_vtotal, bp);

	/* Set vertical display timings */
	regmap_write(tcon->regs, SUN4I_TCON0_BASIC2_REG,
		     SUN4I_TCON0_BASIC2_V_TOTAL(mode->crtc_vtotal * 2) |
		     SUN4I_TCON0_BASIC2_V_BACKPORCH(bp));

	reg = SUN4I_TCON0_LVDS_IF_CLK_SEL_TCON0 |
		SUN4I_TCON0_LVDS_IF_DATA_POL_NORMAL |
		SUN4I_TCON0_LVDS_IF_CLK_POL_NORMAL;
	if (sun4i_tcon_get_pixel_depth(encoder) == 24)
		reg |= SUN4I_TCON0_LVDS_IF_BITWIDTH_24BITS;
	else
		reg |= SUN4I_TCON0_LVDS_IF_BITWIDTH_18BITS;

	regmap_write(tcon->regs, SUN4I_TCON0_LVDS_IF_REG, reg);

	/* Setup the polarity of the various signals */
	if (!(mode->flags & DRM_MODE_FLAG_PHSYNC))
		val |= SUN4I_TCON0_IO_POL_HSYNC_POSITIVE;

	if (!(mode->flags & DRM_MODE_FLAG_PVSYNC))
		val |= SUN4I_TCON0_IO_POL_VSYNC_POSITIVE;

	regmap_write(tcon->regs, SUN4I_TCON0_IO_POL_REG, val);

	/* Map output pins to channel 0 */
	regmap_update_bits(tcon->regs, SUN4I_TCON_GCTL_REG,
			   SUN4I_TCON_GCTL_IOMAP_MASK,
			   SUN4I_TCON_GCTL_IOMAP_TCON0);

	/* Enable the output on the pins */
	regmap_write(tcon->regs, SUN4I_TCON0_IO_TRI_REG, 0xe0000000);
}

static void sun4i_tcon0_mode_set_rgb(struct sun4i_tcon *tcon,
				     const struct drm_display_mode *mode)
{
	struct drm_panel *panel = tcon->panel;
	struct drm_connector *connector = panel->connector;
	struct drm_display_info display_info = connector->display_info;
	unsigned int bp, hsync, vsync;
	u8 clk_delay;
	u32 val = 0;

	WARN_ON(!tcon->quirks->has_channel_0);

	tcon->dclk_min_div = 6;
	tcon->dclk_max_div = 127;
	sun4i_tcon0_mode_set_common(tcon, mode);

	/* Adjust clock delay */
	clk_delay = sun4i_tcon_get_clk_delay(mode, 0);
	regmap_update_bits(tcon->regs, SUN4I_TCON0_CTL_REG,
			   SUN4I_TCON0_CTL_CLK_DELAY_MASK,
			   SUN4I_TCON0_CTL_CLK_DELAY(clk_delay));

	/*
	 * This is called a backporch in the register documentation,
	 * but it really is the back porch + hsync
	 */
	bp = mode->crtc_htotal - mode->crtc_hsync_start;
	DRM_DEBUG_DRIVER("Setting horizontal total %d, backporch %d\n",
			 mode->crtc_htotal, bp);

	/* Set horizontal display timings */
	regmap_write(tcon->regs, SUN4I_TCON0_BASIC1_REG,
		     SUN4I_TCON0_BASIC1_H_TOTAL(mode->crtc_htotal) |
		     SUN4I_TCON0_BASIC1_H_BACKPORCH(bp));

	/*
	 * This is called a backporch in the register documentation,
	 * but it really is the back porch + hsync
	 */
	bp = mode->crtc_vtotal - mode->crtc_vsync_start;
	DRM_DEBUG_DRIVER("Setting vertical total %d, backporch %d\n",
			 mode->crtc_vtotal, bp);

	/* Set vertical display timings */
	regmap_write(tcon->regs, SUN4I_TCON0_BASIC2_REG,
		     SUN4I_TCON0_BASIC2_V_TOTAL(mode->crtc_vtotal * 2) |
		     SUN4I_TCON0_BASIC2_V_BACKPORCH(bp));

	/* Set Hsync and Vsync length */
	hsync = mode->crtc_hsync_end - mode->crtc_hsync_start;
	vsync = mode->crtc_vsync_end - mode->crtc_vsync_start;
	DRM_DEBUG_DRIVER("Setting HSYNC %d, VSYNC %d\n", hsync, vsync);
	regmap_write(tcon->regs, SUN4I_TCON0_BASIC3_REG,
		     SUN4I_TCON0_BASIC3_V_SYNC(vsync) |
		     SUN4I_TCON0_BASIC3_H_SYNC(hsync));

	/* Setup the polarity of the various signals */
	if (mode->flags & DRM_MODE_FLAG_PHSYNC)
		val |= SUN4I_TCON0_IO_POL_HSYNC_POSITIVE;

	if (mode->flags & DRM_MODE_FLAG_PVSYNC)
		val |= SUN4I_TCON0_IO_POL_VSYNC_POSITIVE;

	/*
	 * On A20 and similar SoCs, the only way to achieve Positive Edge
	 * (Rising Edge), is setting dclk clock phase to 2/3(240°).
	 * By default TCON works in Negative Edge(Falling Edge),
	 * this is why phase is set to 0 in that case.
	 * Unfortunately there's no way to logically invert dclk through
	 * IO_POL register.
	 * The only acceptable way to work, triple checked with scope,
	 * is using clock phase set to 0° for Negative Edge and set to 240°
	 * for Positive Edge.
	 * On A33 and similar SoCs there would be a 90° phase option,
	 * but it divides also dclk by 2.
	 * Following code is a way to avoid quirks all around TCON
	 * and DOTCLOCK drivers.
	 */
	if (display_info.bus_flags & DRM_BUS_FLAG_PIXDATA_POSEDGE)
		clk_set_phase(tcon->dclk, 240);

	if (display_info.bus_flags & DRM_BUS_FLAG_PIXDATA_NEGEDGE)
		clk_set_phase(tcon->dclk, 0);

	regmap_update_bits(tcon->regs, SUN4I_TCON0_IO_POL_REG,
			   SUN4I_TCON0_IO_POL_HSYNC_POSITIVE | SUN4I_TCON0_IO_POL_VSYNC_POSITIVE,
			   val);

	/* Map output pins to channel 0 */
	regmap_update_bits(tcon->regs, SUN4I_TCON_GCTL_REG,
			   SUN4I_TCON_GCTL_IOMAP_MASK,
			   SUN4I_TCON_GCTL_IOMAP_TCON0);

	/* Enable the output on the pins */
	regmap_write(tcon->regs, SUN4I_TCON0_IO_TRI_REG, 0);
}

static void sun4i_tcon1_mode_set(struct sun4i_tcon *tcon,
				 const struct drm_display_mode *mode)
{
	unsigned int bp, hsync, vsync, vtotal;
	u8 clk_delay;
	u32 val;

	WARN_ON(!tcon->quirks->has_channel_1);

	/* Configure the dot clock */
	clk_set_rate(tcon->sclk1, mode->crtc_clock * 1000);

	/* Adjust clock delay */
	clk_delay = sun4i_tcon_get_clk_delay(mode, 1);
	regmap_update_bits(tcon->regs, SUN4I_TCON1_CTL_REG,
			   SUN4I_TCON1_CTL_CLK_DELAY_MASK,
			   SUN4I_TCON1_CTL_CLK_DELAY(clk_delay));

	/* Set interlaced mode */
	if (mode->flags & DRM_MODE_FLAG_INTERLACE)
		val = SUN4I_TCON1_CTL_INTERLACE_ENABLE;
	else
		val = 0;
	regmap_update_bits(tcon->regs, SUN4I_TCON1_CTL_REG,
			   SUN4I_TCON1_CTL_INTERLACE_ENABLE,
			   val);

	/* Set the input resolution */
	regmap_write(tcon->regs, SUN4I_TCON1_BASIC0_REG,
		     SUN4I_TCON1_BASIC0_X(mode->crtc_hdisplay) |
		     SUN4I_TCON1_BASIC0_Y(mode->crtc_vdisplay));

	/* Set the upscaling resolution */
	regmap_write(tcon->regs, SUN4I_TCON1_BASIC1_REG,
		     SUN4I_TCON1_BASIC1_X(mode->crtc_hdisplay) |
		     SUN4I_TCON1_BASIC1_Y(mode->crtc_vdisplay));

	/* Set the output resolution */
	regmap_write(tcon->regs, SUN4I_TCON1_BASIC2_REG,
		     SUN4I_TCON1_BASIC2_X(mode->crtc_hdisplay) |
		     SUN4I_TCON1_BASIC2_Y(mode->crtc_vdisplay));

	/* Set horizontal display timings */
	bp = mode->crtc_htotal - mode->crtc_hsync_start;
	DRM_DEBUG_DRIVER("Setting horizontal total %d, backporch %d\n",
			 mode->htotal, bp);
	regmap_write(tcon->regs, SUN4I_TCON1_BASIC3_REG,
		     SUN4I_TCON1_BASIC3_H_TOTAL(mode->crtc_htotal) |
		     SUN4I_TCON1_BASIC3_H_BACKPORCH(bp));

	bp = mode->crtc_vtotal - mode->crtc_vsync_start;
	DRM_DEBUG_DRIVER("Setting vertical total %d, backporch %d\n",
			 mode->crtc_vtotal, bp);

	/*
	 * The vertical resolution needs to be doubled in all
	 * cases. We could use crtc_vtotal and always multiply by two,
	 * but that leads to a rounding error in interlace when vtotal
	 * is odd.
	 *
	 * This happens with TV's PAL for example, where vtotal will
	 * be 625, crtc_vtotal 312, and thus crtc_vtotal * 2 will be
	 * 624, which apparently confuses the hardware.
	 *
	 * To work around this, we will always use vtotal, and
	 * multiply by two only if we're not in interlace.
	 */
	vtotal = mode->vtotal;
	if (!(mode->flags & DRM_MODE_FLAG_INTERLACE))
		vtotal = vtotal * 2;

	/* Set vertical display timings */
	regmap_write(tcon->regs, SUN4I_TCON1_BASIC4_REG,
		     SUN4I_TCON1_BASIC4_V_TOTAL(vtotal) |
		     SUN4I_TCON1_BASIC4_V_BACKPORCH(bp));

	/* Set Hsync and Vsync length */
	hsync = mode->crtc_hsync_end - mode->crtc_hsync_start;
	vsync = mode->crtc_vsync_end - mode->crtc_vsync_start;
	DRM_DEBUG_DRIVER("Setting HSYNC %d, VSYNC %d\n", hsync, vsync);
	regmap_write(tcon->regs, SUN4I_TCON1_BASIC5_REG,
		     SUN4I_TCON1_BASIC5_V_SYNC(vsync) |
		     SUN4I_TCON1_BASIC5_H_SYNC(hsync));

	/* Map output pins to channel 1 */
	regmap_update_bits(tcon->regs, SUN4I_TCON_GCTL_REG,
			   SUN4I_TCON_GCTL_IOMAP_MASK,
			   SUN4I_TCON_GCTL_IOMAP_TCON1);
}

void sun4i_tcon_mode_set(struct sun4i_tcon *tcon,
			 const struct drm_encoder *encoder,
			 const struct drm_display_mode *mode)
{
	switch (encoder->encoder_type) {
	case DRM_MODE_ENCODER_LVDS:
		sun4i_tcon0_mode_set_lvds(tcon, encoder, mode);
		break;
	case DRM_MODE_ENCODER_NONE:
		sun4i_tcon0_mode_set_rgb(tcon, mode);
		sun4i_tcon_set_mux(tcon, 0, encoder);
		break;
	case DRM_MODE_ENCODER_TVDAC:
	case DRM_MODE_ENCODER_TMDS:
		sun4i_tcon1_mode_set(tcon, mode);
		sun4i_tcon_set_mux(tcon, 1, encoder);
		break;
	default:
		DRM_DEBUG_DRIVER("Unknown encoder type, doing nothing...\n");
	}
}
EXPORT_SYMBOL(sun4i_tcon_mode_set);

static void sun4i_tcon_finish_page_flip(struct drm_device *dev,
					struct sun4i_crtc *scrtc)
{
	unsigned long flags;

	spin_lock_irqsave(&dev->event_lock, flags);
	if (scrtc->event) {
		drm_crtc_send_vblank_event(&scrtc->crtc, scrtc->event);
		drm_crtc_vblank_put(&scrtc->crtc);
		scrtc->event = NULL;
	}
	spin_unlock_irqrestore(&dev->event_lock, flags);
}

static irqreturn_t sun4i_tcon_handler(int irq, void *private)
{
	struct sun4i_tcon *tcon = private;
	struct drm_device *drm = tcon->drm;
	struct sun4i_crtc *scrtc = tcon->crtc;
	struct sunxi_engine *engine = scrtc->engine;
	unsigned int status;

	regmap_read(tcon->regs, SUN4I_TCON_GINT0_REG, &status);

	if (!(status & (SUN4I_TCON_GINT0_VBLANK_INT(0) |
			SUN4I_TCON_GINT0_VBLANK_INT(1))))
		return IRQ_NONE;

	drm_crtc_handle_vblank(&scrtc->crtc);
	sun4i_tcon_finish_page_flip(drm, scrtc);

	/* Acknowledge the interrupt */
	regmap_update_bits(tcon->regs, SUN4I_TCON_GINT0_REG,
			   SUN4I_TCON_GINT0_VBLANK_INT(0) |
			   SUN4I_TCON_GINT0_VBLANK_INT(1),
			   0);

	if (engine->ops->vblank_quirk)
		engine->ops->vblank_quirk(engine);

	return IRQ_HANDLED;
}

static int sun4i_tcon_init_clocks(struct device *dev,
				  struct sun4i_tcon *tcon)
{
	tcon->clk = devm_clk_get(dev, "ahb");
	if (IS_ERR(tcon->clk)) {
		dev_err(dev, "Couldn't get the TCON bus clock\n");
		return PTR_ERR(tcon->clk);
	}
	clk_prepare_enable(tcon->clk);

	if (tcon->quirks->has_channel_0) {
		tcon->sclk0 = devm_clk_get(dev, "tcon-ch0");
		if (IS_ERR(tcon->sclk0)) {
			dev_err(dev, "Couldn't get the TCON channel 0 clock\n");
			return PTR_ERR(tcon->sclk0);
		}
	}

	if (tcon->quirks->has_channel_1) {
		tcon->sclk1 = devm_clk_get(dev, "tcon-ch1");
		if (IS_ERR(tcon->sclk1)) {
			dev_err(dev, "Couldn't get the TCON channel 1 clock\n");
			return PTR_ERR(tcon->sclk1);
		}
	}

	return 0;
}

static void sun4i_tcon_free_clocks(struct sun4i_tcon *tcon)
{
	clk_disable_unprepare(tcon->clk);
}

static int sun4i_tcon_init_irq(struct device *dev,
			       struct sun4i_tcon *tcon)
{
	struct platform_device *pdev = to_platform_device(dev);
	int irq, ret;

	irq = platform_get_irq(pdev, 0);
	if (irq < 0) {
		dev_err(dev, "Couldn't retrieve the TCON interrupt\n");
		return irq;
	}

	ret = devm_request_irq(dev, irq, sun4i_tcon_handler, 0,
			       dev_name(dev), tcon);
	if (ret) {
		dev_err(dev, "Couldn't request the IRQ\n");
		return ret;
	}

	return 0;
}

static struct regmap_config sun4i_tcon_regmap_config = {
	.reg_bits	= 32,
	.val_bits	= 32,
	.reg_stride	= 4,
	.max_register	= 0x800,
};

static int sun4i_tcon_init_regmap(struct device *dev,
				  struct sun4i_tcon *tcon)
{
	struct platform_device *pdev = to_platform_device(dev);
	struct resource *res;
	void __iomem *regs;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	regs = devm_ioremap_resource(dev, res);
	if (IS_ERR(regs))
		return PTR_ERR(regs);

	tcon->regs = devm_regmap_init_mmio(dev, regs,
					   &sun4i_tcon_regmap_config);
	if (IS_ERR(tcon->regs)) {
		dev_err(dev, "Couldn't create the TCON regmap\n");
		return PTR_ERR(tcon->regs);
	}

	/* Make sure the TCON is disabled and all IRQs are off */
	regmap_write(tcon->regs, SUN4I_TCON_GCTL_REG, 0);
	regmap_write(tcon->regs, SUN4I_TCON_GINT0_REG, 0);
	regmap_write(tcon->regs, SUN4I_TCON_GINT1_REG, 0);

	/* Disable IO lines and set them to tristate */
	regmap_write(tcon->regs, SUN4I_TCON0_IO_TRI_REG, ~0);
	regmap_write(tcon->regs, SUN4I_TCON1_IO_TRI_REG, ~0);

	return 0;
}

/*
 * On SoCs with the old display pipeline design (Display Engine 1.0),
 * the TCON is always tied to just one backend. Hence we can traverse
 * the of_graph upwards to find the backend our tcon is connected to,
 * and take its ID as our own.
 *
 * We can either identify backends from their compatible strings, which
 * means maintaining a large list of them. Or, since the backend is
 * registered and binded before the TCON, we can just go through the
 * list of registered backends and compare the device node.
 *
 * As the structures now store engines instead of backends, here this
 * function in fact searches the corresponding engine, and the ID is
 * requested via the get_id function of the engine.
 */
static struct sunxi_engine *
sun4i_tcon_find_engine_traverse(struct sun4i_drv *drv,
				struct device_node *node)
{
	struct device_node *port, *ep, *remote;
	struct sunxi_engine *engine = ERR_PTR(-EINVAL);

	port = of_graph_get_port_by_id(node, 0);
	if (!port)
		return ERR_PTR(-EINVAL);

	/*
	 * This only works if there is only one path from the TCON
	 * to any display engine. Otherwise the probe order of the
	 * TCONs and display engines is not guaranteed. They may
	 * either bind to the wrong one, or worse, bind to the same
	 * one if additional checks are not done.
	 *
	 * Bail out if there are multiple input connections.
	 */
	if (of_get_available_child_count(port) != 1)
		goto out_put_port;

	/* Get the first connection without specifying an ID */
	ep = of_get_next_available_child(port, NULL);
	if (!ep)
		goto out_put_port;

	remote = of_graph_get_remote_port_parent(ep);
	if (!remote)
		goto out_put_ep;

	/* does this node match any registered engines? */
	list_for_each_entry(engine, &drv->engine_list, list)
		if (remote == engine->node)
			goto out_put_remote;

	/* keep looking through upstream ports */
	engine = sun4i_tcon_find_engine_traverse(drv, remote);

out_put_remote:
	of_node_put(remote);
out_put_ep:
	of_node_put(ep);
out_put_port:
	of_node_put(port);

	return engine;
}

/*
 * The device tree binding says that the remote endpoint ID of any
 * connection between components, up to and including the TCON, of
 * the display pipeline should be equal to the actual ID of the local
 * component. Thus we can look at any one of the input connections of
 * the TCONs, and use that connection's remote endpoint ID as our own.
 *
 * Since the user of this function already finds the input port,
 * the port is passed in directly without further checks.
 */
static int sun4i_tcon_of_get_id_from_port(struct device_node *port)
{
	struct device_node *ep;
	int ret = -EINVAL;

	/* try finding an upstream endpoint */
	for_each_available_child_of_node(port, ep) {
		struct device_node *remote;
		u32 reg;

		remote = of_graph_get_remote_endpoint(ep);
		if (!remote)
			continue;

		ret = of_property_read_u32(remote, "reg", &reg);
		if (ret)
			continue;

		ret = reg;
	}

	return ret;
}

/*
 * Once we know the TCON's id, we can look through the list of
 * engines to find a matching one. We assume all engines have
 * been probed and added to the list.
 */
static struct sunxi_engine *sun4i_tcon_get_engine_by_id(struct sun4i_drv *drv,
							int id)
{
	struct sunxi_engine *engine;

	list_for_each_entry(engine, &drv->engine_list, list)
		if (engine->id == id)
			return engine;

	return ERR_PTR(-EINVAL);
}

/*
 * On SoCs with the old display pipeline design (Display Engine 1.0),
 * we assumed the TCON was always tied to just one backend. However
 * this proved not to be the case. On the A31, the TCON can select
 * either backend as its source. On the A20 (and likely on the A10),
 * the backend can choose which TCON to output to.
 *
 * The device tree binding says that the remote endpoint ID of any
 * connection between components, up to and including the TCON, of
 * the display pipeline should be equal to the actual ID of the local
 * component. Thus we should be able to look at any one of the input
 * connections of the TCONs, and use that connection's remote endpoint
 * ID as our own.
 *
 * However  the connections between the backend and TCON were assumed
 * to be always singular, and their endpoit IDs were all incorrectly
 * set to 0. This means for these old device trees, we cannot just look
 * up the remote endpoint ID of a TCON input endpoint. TCON1 would be
 * incorrectly identified as TCON0.
 *
 * This function first checks if the TCON node has 2 input endpoints.
 * If so, then the device tree is a corrected version, and it will use
 * sun4i_tcon_of_get_id() and sun4i_tcon_get_engine_by_id() from above
 * to fetch the ID and engine directly. If not, then it is likely an
 * old device trees, where the endpoint IDs were incorrect, but did not
 * have endpoint connections between the backend and TCON across
 * different display pipelines. It will fall back to the old method of
 * traversing the  of_graph to try and find a matching engine by device
 * node.
 *
 * In the case of single display pipeline device trees, either method
 * works.
 */
static struct sunxi_engine *sun4i_tcon_find_engine(struct sun4i_drv *drv,
						   struct device_node *node)
{
	struct device_node *port;
	struct sunxi_engine *engine;

	port = of_graph_get_port_by_id(node, 0);
	if (!port)
		return ERR_PTR(-EINVAL);

	/*
	 * Is this a corrected device tree with cross pipeline
	 * connections between the backend and TCON?
	 */
	if (of_get_child_count(port) > 1) {
		/* Get our ID directly from an upstream endpoint */
		int id = sun4i_tcon_of_get_id_from_port(port);

		/* Get our engine by matching our ID */
		engine = sun4i_tcon_get_engine_by_id(drv, id);

		of_node_put(port);
		return engine;
	}

	/* Fallback to old method by traversing input endpoints */
	of_node_put(port);
	return sun4i_tcon_find_engine_traverse(drv, node);
}

static int sun4i_tcon_bind(struct device *dev, struct device *master,
			   void *data)
{
	struct drm_device *drm = data;
	struct sun4i_drv *drv = drm->dev_private;
	struct sunxi_engine *engine;
	struct device_node *remote;
	struct sun4i_tcon *tcon;
	struct reset_control *edp_rstc;
	bool has_lvds_rst, has_lvds_alt, can_lvds;
	int ret;

	engine = sun4i_tcon_find_engine(drv, dev->of_node);
	if (IS_ERR(engine)) {
		dev_err(dev, "Couldn't find matching engine\n");
		return -EPROBE_DEFER;
	}

	tcon = devm_kzalloc(dev, sizeof(*tcon), GFP_KERNEL);
	if (!tcon)
		return -ENOMEM;
	dev_set_drvdata(dev, tcon);
	tcon->drm = drm;
	tcon->dev = dev;
	tcon->id = engine->id;
	tcon->quirks = of_device_get_match_data(dev);

	tcon->lcd_rst = devm_reset_control_get(dev, "lcd");
	if (IS_ERR(tcon->lcd_rst)) {
		dev_err(dev, "Couldn't get our reset line\n");
		return PTR_ERR(tcon->lcd_rst);
	}

	if (tcon->quirks->needs_edp_reset) {
		edp_rstc = devm_reset_control_get_shared(dev, "edp");
		if (IS_ERR(edp_rstc)) {
			dev_err(dev, "Couldn't get edp reset line\n");
			return PTR_ERR(edp_rstc);
		}

		ret = reset_control_deassert(edp_rstc);
		if (ret) {
			dev_err(dev, "Couldn't deassert edp reset line\n");
			return ret;
		}
	}

	/* Make sure our TCON is reset */
	ret = reset_control_reset(tcon->lcd_rst);
	if (ret) {
		dev_err(dev, "Couldn't deassert our reset line\n");
		return ret;
	}

	if (tcon->quirks->supports_lvds) {
		/*
		 * This can only be made optional since we've had DT
		 * nodes without the LVDS reset properties.
		 *
		 * If the property is missing, just disable LVDS, and
		 * print a warning.
		 */
		tcon->lvds_rst = devm_reset_control_get_optional(dev, "lvds");
		if (IS_ERR(tcon->lvds_rst)) {
			dev_err(dev, "Couldn't get our reset line\n");
			return PTR_ERR(tcon->lvds_rst);
		} else if (tcon->lvds_rst) {
			has_lvds_rst = true;
			reset_control_reset(tcon->lvds_rst);
		} else {
			has_lvds_rst = false;
		}

		/*
		 * This can only be made optional since we've had DT
		 * nodes without the LVDS reset properties.
		 *
		 * If the property is missing, just disable LVDS, and
		 * print a warning.
		 */
		if (tcon->quirks->has_lvds_alt) {
			tcon->lvds_pll = devm_clk_get(dev, "lvds-alt");
			if (IS_ERR(tcon->lvds_pll)) {
				if (PTR_ERR(tcon->lvds_pll) == -ENOENT) {
					has_lvds_alt = false;
				} else {
					dev_err(dev, "Couldn't get the LVDS PLL\n");
					return PTR_ERR(tcon->lvds_pll);
				}
			} else {
				has_lvds_alt = true;
			}
		}

		if (!has_lvds_rst ||
		    (tcon->quirks->has_lvds_alt && !has_lvds_alt)) {
			dev_warn(dev, "Missing LVDS properties, Please upgrade your DT\n");
			dev_warn(dev, "LVDS output disabled\n");
			can_lvds = false;
		} else {
			can_lvds = true;
		}
	} else {
		can_lvds = false;
	}

	ret = sun4i_tcon_init_clocks(dev, tcon);
	if (ret) {
		dev_err(dev, "Couldn't init our TCON clocks\n");
		goto err_assert_reset;
	}

	ret = sun4i_tcon_init_regmap(dev, tcon);
	if (ret) {
		dev_err(dev, "Couldn't init our TCON regmap\n");
		goto err_free_clocks;
	}

	if (tcon->quirks->has_channel_0) {
		ret = sun4i_dclk_create(dev, tcon);
		if (ret) {
			dev_err(dev, "Couldn't create our TCON dot clock\n");
			goto err_free_clocks;
		}
	}

	ret = sun4i_tcon_init_irq(dev, tcon);
	if (ret) {
		dev_err(dev, "Couldn't init our TCON interrupts\n");
		goto err_free_dotclock;
	}

	tcon->crtc = sun4i_crtc_init(drm, engine, tcon);
	if (IS_ERR(tcon->crtc)) {
		dev_err(dev, "Couldn't create our CRTC\n");
		ret = PTR_ERR(tcon->crtc);
		goto err_free_dotclock;
	}

	/*
	 * If we have an LVDS panel connected to the TCON, we should
	 * just probe the LVDS connector. Otherwise, just probe RGB as
	 * we used to.
	 */
	remote = of_graph_get_remote_node(dev->of_node, 1, 0);
	if (of_device_is_compatible(remote, "panel-lvds"))
		if (can_lvds)
			ret = sun4i_lvds_init(drm, tcon);
		else
			ret = -EINVAL;
	else
		ret = sun4i_rgb_init(drm, tcon);
	of_node_put(remote);

	if (ret < 0)
		goto err_free_dotclock;

	if (tcon->quirks->needs_de_be_mux) {
		/*
		 * We assume there is no dynamic muxing of backends
		 * and TCONs, so we select the backend with same ID.
		 *
		 * While dynamic selection might be interesting, since
		 * the CRTC is tied to the TCON, while the layers are
		 * tied to the backends, this means, we will need to
		 * switch between groups of layers. There might not be
		 * a way to represent this constraint in DRM.
		 */
		regmap_update_bits(tcon->regs, SUN4I_TCON0_CTL_REG,
				   SUN4I_TCON0_CTL_SRC_SEL_MASK,
				   tcon->id);
		regmap_update_bits(tcon->regs, SUN4I_TCON1_CTL_REG,
				   SUN4I_TCON1_CTL_SRC_SEL_MASK,
				   tcon->id);
	}

	list_add_tail(&tcon->list, &drv->tcon_list);

	return 0;

err_free_dotclock:
	if (tcon->quirks->has_channel_0)
		sun4i_dclk_free(tcon);
err_free_clocks:
	sun4i_tcon_free_clocks(tcon);
err_assert_reset:
	reset_control_assert(tcon->lcd_rst);
	return ret;
}

static void sun4i_tcon_unbind(struct device *dev, struct device *master,
			      void *data)
{
	struct sun4i_tcon *tcon = dev_get_drvdata(dev);

	list_del(&tcon->list);
	if (tcon->quirks->has_channel_0)
		sun4i_dclk_free(tcon);
	sun4i_tcon_free_clocks(tcon);
}

static const struct component_ops sun4i_tcon_ops = {
	.bind	= sun4i_tcon_bind,
	.unbind	= sun4i_tcon_unbind,
};

static int sun4i_tcon_probe(struct platform_device *pdev)
{
	struct device_node *node = pdev->dev.of_node;
	struct drm_bridge *bridge;
	struct drm_panel *panel;
	int ret;

	ret = drm_of_find_panel_or_bridge(node, 1, 0, &panel, &bridge);
	if (ret == -EPROBE_DEFER)
		return ret;

	return component_add(&pdev->dev, &sun4i_tcon_ops);
}

static int sun4i_tcon_remove(struct platform_device *pdev)
{
	component_del(&pdev->dev, &sun4i_tcon_ops);

	return 0;
}

/* platform specific TCON muxing callbacks */
static int sun4i_a10_tcon_set_mux(struct sun4i_tcon *tcon,
				  const struct drm_encoder *encoder)
{
	struct sun4i_tcon *tcon0 = sun4i_get_tcon0(encoder->dev);
	u32 shift;

	if (!tcon0)
		return -EINVAL;

	switch (encoder->encoder_type) {
	case DRM_MODE_ENCODER_TMDS:
		/* HDMI */
		shift = 8;
		break;
	default:
		return -EINVAL;
	}

	regmap_update_bits(tcon0->regs, SUN4I_TCON_MUX_CTRL_REG,
			   0x3 << shift, tcon->id << shift);

	return 0;
}

static int sun5i_a13_tcon_set_mux(struct sun4i_tcon *tcon,
				  const struct drm_encoder *encoder)
{
	u32 val;

	if (encoder->encoder_type == DRM_MODE_ENCODER_TVDAC)
		val = 1;
	else
		val = 0;

	/*
	 * FIXME: Undocumented bits
	 */
	return regmap_write(tcon->regs, SUN4I_TCON_MUX_CTRL_REG, val);
}

static int sun6i_tcon_set_mux(struct sun4i_tcon *tcon,
			      const struct drm_encoder *encoder)
{
	struct sun4i_tcon *tcon0 = sun4i_get_tcon0(encoder->dev);
	u32 shift;

	if (!tcon0)
		return -EINVAL;

	switch (encoder->encoder_type) {
	case DRM_MODE_ENCODER_TMDS:
		/* HDMI */
		shift = 8;
		break;
	default:
		/* TODO A31 has MIPI DSI but A31s does not */
		return -EINVAL;
	}

	regmap_update_bits(tcon0->regs, SUN4I_TCON_MUX_CTRL_REG,
			   0x3 << shift, tcon->id << shift);

	return 0;
}

static const struct sun4i_tcon_quirks sun4i_a10_quirks = {
	.has_channel_0		= true,
	.has_channel_1		= true,
	.set_mux		= sun4i_a10_tcon_set_mux,
};

static const struct sun4i_tcon_quirks sun5i_a13_quirks = {
	.has_channel_0		= true,
	.has_channel_1		= true,
	.set_mux		= sun5i_a13_tcon_set_mux,
};

static const struct sun4i_tcon_quirks sun6i_a31_quirks = {
	.has_channel_0		= true,
	.has_channel_1		= true,
	.has_lvds_alt		= true,
	.needs_de_be_mux	= true,
	.set_mux		= sun6i_tcon_set_mux,
};

static const struct sun4i_tcon_quirks sun6i_a31s_quirks = {
	.has_channel_0		= true,
	.has_channel_1		= true,
	.needs_de_be_mux	= true,
};

static const struct sun4i_tcon_quirks sun7i_a20_quirks = {
	.has_channel_0		= true,
	.has_channel_1		= true,
	/* Same display pipeline structure as A10 */
	.set_mux		= sun4i_a10_tcon_set_mux,
};

static const struct sun4i_tcon_quirks sun8i_a33_quirks = {
	.has_channel_0		= true,
	.has_lvds_alt		= true,
};

static const struct sun4i_tcon_quirks sun8i_a83t_lcd_quirks = {
	.supports_lvds		= true,
	.has_channel_0		= true,
};

static const struct sun4i_tcon_quirks sun8i_a83t_tv_quirks = {
	.has_channel_1		= true,
};

static const struct sun4i_tcon_quirks sun8i_v3s_quirks = {
	.has_channel_0		= true,
};

static const struct sun4i_tcon_quirks sun9i_a80_tcon_lcd_quirks = {
	.has_channel_0	= true,
	.needs_edp_reset = true,
};

static const struct sun4i_tcon_quirks sun9i_a80_tcon_tv_quirks = {
	.has_channel_1	= true,
	.needs_edp_reset = true,
};

/* sun4i_drv uses this list to check if a device node is a TCON */
const struct of_device_id sun4i_tcon_of_table[] = {
	{ .compatible = "allwinner,sun4i-a10-tcon", .data = &sun4i_a10_quirks },
	{ .compatible = "allwinner,sun5i-a13-tcon", .data = &sun5i_a13_quirks },
	{ .compatible = "allwinner,sun6i-a31-tcon", .data = &sun6i_a31_quirks },
	{ .compatible = "allwinner,sun6i-a31s-tcon", .data = &sun6i_a31s_quirks },
	{ .compatible = "allwinner,sun7i-a20-tcon", .data = &sun7i_a20_quirks },
	{ .compatible = "allwinner,sun8i-a33-tcon", .data = &sun8i_a33_quirks },
	{ .compatible = "allwinner,sun8i-a83t-tcon-lcd", .data = &sun8i_a83t_lcd_quirks },
	{ .compatible = "allwinner,sun8i-a83t-tcon-tv", .data = &sun8i_a83t_tv_quirks },
	{ .compatible = "allwinner,sun8i-v3s-tcon", .data = &sun8i_v3s_quirks },
	{ .compatible = "allwinner,sun9i-a80-tcon-lcd", .data = &sun9i_a80_tcon_lcd_quirks },
	{ .compatible = "allwinner,sun9i-a80-tcon-tv", .data = &sun9i_a80_tcon_tv_quirks },
	{ }
};
MODULE_DEVICE_TABLE(of, sun4i_tcon_of_table);
EXPORT_SYMBOL(sun4i_tcon_of_table);

static struct platform_driver sun4i_tcon_platform_driver = {
	.probe		= sun4i_tcon_probe,
	.remove		= sun4i_tcon_remove,
	.driver		= {
		.name		= "sun4i-tcon",
		.of_match_table	= sun4i_tcon_of_table,
	},
};
module_platform_driver(sun4i_tcon_platform_driver);

MODULE_AUTHOR("Maxime Ripard <maxime.ripard@free-electrons.com>");
MODULE_DESCRIPTION("Allwinner A10 Timing Controller Driver");
MODULE_LICENSE("GPL");
