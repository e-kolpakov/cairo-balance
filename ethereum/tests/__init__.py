import sys, os

current_folder = os.path.dirname(__file__)
brownie_root = os.path.dirname(current_folder)
project_root = os.path.dirname(brownie_root)
oracle_root = os.path.join(project_root, 'oracle')

sys.path.append(current_folder)
sys.path.append(oracle_root)