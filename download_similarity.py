import os
import gdown

FILE_ID = "10gCOBvZVC6ggddyQoFISuN3PMs2UZ90h"

URL = f"https://drive.google.com/uc?id={FILE_ID}"

MODEL_PATH = "model/similarity.pkl"

os.makedirs("model", exist_ok=True)

if not os.path.exists(MODEL_PATH):
    print("Downloading similarity.pkl...")
    gdown.download(URL, MODEL_PATH, quiet=False)
else:
    print("similarity.pkl already exists.")