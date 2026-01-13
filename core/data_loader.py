import pandas as pd

def load_and_clean_data(file):
    df = pd.read_excel(file,  header=2)
    columns = ['Date operation', 'Type operation',
        'Libelle operation', 'Montant operation en euro'] #, 'Libelle court',
    df = df [columns]
    df.rename(columns={'Date operation': 'date_operation', 'Type operation': 'type', 'Libelle operation': 'operation', 'Montant operation en euro': 'montant'}, inplace=True)
    df['date_operation'] = pd.to_datetime(df['date_operation'])
    # Remplacer uniquement les motifs du type 1234XXXXXXXX1234
    df["operation"] = df["operation"].str.replace(
        r'\b\d{4}X{8}\d{4}\b',   # motif : 4 chiffres, 8 X, 4 chiffres
        lambda m: 'X' * len(m.group(0)),  # remplace par le même nombre de X
        regex=True
    )
    return df

