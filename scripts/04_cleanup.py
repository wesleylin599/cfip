import shutil
import os


for directory in [
    "parts",
    "results"
]:

    if os.path.exists(directory):

        shutil.rmtree(directory)

        print(
            f"Removed {directory}"
        )
