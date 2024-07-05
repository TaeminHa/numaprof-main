import matplotlib.pyplot as plt

# New datasets from the experiment
iterations_new = list(range(1, 21))
new_time = [
    210.72235796198947, 210.95934394199867, 213.86330917899613, 210.579969598999,
    214.65111076399626, 211.98276158299996, 210.83646090999537, 215.24316892000206,
    209.60206677899987, 210.97803515598935, 211.2775117650017, 211.19044298499648,
    211.45876362299896, 210.61583699499897, 213.50115353, 210.17692340099893,
    216.04484091799532, 214.68691227400268, 211.12237240599643, 210.994046480002
]

new_page_migration_count = [
    1381967, 1362898, 2033719, 1215489, 2055385, 1464221, 1270320, 2010038,
    1126152, 1368304, 1419529, 1340184, 1298814, 1300447, 2031369, 1339602,
    2036733, 2015665, 1390156, 1371973
]

# Create the figure and the first axis
fig, ax1 = plt.subplots()

# Plot TIME on the left y-axis
ax1.set_xlabel('Iteration')
ax1.set_ylabel('Time (seconds)', color='tab:blue')
ax1.plot(iterations_new, new_time, color='tab:blue', marker='o', label='Time')
ax1.tick_params(axis='y', labelcolor='tab:blue')
ax1.set_xticks(iterations_new)

# Create a second y-axis for PAGE MIGRATION COUNT
ax2 = ax1.twinx()
ax2.set_ylabel('Page Migration Count', color='tab:orange')
ax2.plot(iterations_new, new_page_migration_count, color='tab:orange', marker='x', label='Page Migration Count')
ax2.tick_params(axis='y', labelcolor='tab:orange')

# Add title and grid
plt.title('Time and Page Migration Count per Iteration')
fig.tight_layout()
plt.grid(True)

# Show the plot
plt.savefig('page_migration_time.png')