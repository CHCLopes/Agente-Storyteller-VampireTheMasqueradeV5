import os

def create_tree():
    directories = [
        "bin",
        "models",
        "data/saves",
        "logs"
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for directory in directories:
        path = os.path.join(base_dir, directory)
        os.makedirs(path, exist_ok=True)
        print(f"Directory verified/created: {path}")

if __name__ == "__main__":
    create_tree()
