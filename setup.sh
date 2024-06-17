#!/bin/bash

# install pintool
wget https://software.intel.com/sites/landingpage/pintool/downloads/pin-3.30-98830-g1d7b601b3-gcc-linux.tar.gz
tar xvf pin-3.30-98830-g1d7b601b3-gcc-linux.tar.gz
rm pin-3.30-98830-g1d7b601b3-gcc-linux.tar.gz
mv pin-3.30-98830-g1d7b601b3-gcc-linux pin-3.30

# install numaprof
git clone https://github.com/TaeminHa/numaprof-main.git
mv numaprof-main numaprof

# set path for pintool
echo export PINTOOL_PATH=/users/taeminha/pin-3.30 >> ~/.bashrc
echo export PATH=/users/taeminha/numaprof/build/bin:$PATH >> ~/.bashrc
source ~/.bashrc

# setup numaprof
sudo apt-get update
sudo apt-get install -y libnuma-dev
sudo apt-get install -y cmake
sudo apt-get install -y python3-pip
sudo apt-get install -y npm

cd ./numaprof
mkdir build
cd build

../configure --prefix=./ --with-pintool=$PINTOOL_PATH
make -j
make install

# now we have numaprof installed/setup
cd ../
mkdir results

# install custom linux version with sysctl vars exposed to /proc
git clone https://github.com/TaeminHa/linux-custom.git
cd linux-custom

sudo apt install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev fakeroot dwarves
cp -v /boot/config-$(uname -r) .config
yes "" | make localmodconfig
scripts/config --disable SYSTEM_TRUSTED_KEYS
scripts/config --disable SYSTEM_REVOCATION_KEYS

yes "" | fakeroot make -j32
yes "" | sudo make modules_install
yes "" | sudo make install

sudo reboot
