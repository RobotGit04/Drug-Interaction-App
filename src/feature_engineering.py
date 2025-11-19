import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs

def smiles_to_morgan(smiles: str, radius=2, nBits=2048):
    """Convert SMILES string to Morgan fingerprint vector."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits)
    arr = np.zeros((nBits,), dtype=np.int8)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr

def create_pair_features(smiles1, smiles2):
    fp1 = smiles_to_morgan(smiles1)
    fp2 = smiles_to_morgan(smiles2)
    if fp1 is None or fp2 is None:
        return None
    return np.concatenate([fp1, fp2])  # final size = 4096
