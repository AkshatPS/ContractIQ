import os

def get_filename(path):
    return os.path.splitext(os.path.basename(path))[0]