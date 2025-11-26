import pandas as pd
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import  AgentExecutor, create_tool_calling_agent #tool_calling_agent
from sklearn.linear_model import LinearRegression
import prompts
from dotenv import load_dotenv

load_dotenv()
df = None

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


@tool
def analyze_transactions() -> dict:
    """
    Calcule (vue d'ensemble rapide):

    - Total des revenus et dépenses
    - Breakdown mensuel des revenus et dépenses
    
    Utilise cette fonction pour des demandes à réponses simples et rapide, comme:
    - "Combien j'ai dépensé à un tel mois ?"
    - "Quel est mon total de revenus ?"
    - Obtenir un résumé financier mensuel simple
    - un aperçu des finances global et simple

    Important:
     - Réponds simplement et naturellement.
     - Ignore les structures définit dans d'autres docstrings
    Returns:
        Dict avec summary (totaux) et by_month (détail mensuel)
    """
    global df 
    total_revenue = df[df['montant']>0]['montant'].sum()
    total_expenses = df[df['montant']<0]['montant'].abs().sum()

    # Group by année ET mois
    monthly_revenue = df[df['montant']>0].groupby([
        df['date_operation'].dt.year,
        df['date_operation'].dt.month
    ])['montant'].sum().to_dict()

    monthly_expenses = df[df['montant']<0].groupby([
        df['date_operation'].dt.year,
        df['date_operation'].dt.month
    ])['montant'].sum().abs().to_dict()

    # Les clés sont maintenant des tuples (2024, 12), (2025, 1), etc.
    monthly_breakdown = {}
    all_months = set(list(monthly_revenue.keys()) + list(monthly_expenses.keys()))
    #print('all_months ', all_months)

    for (year, month) in sorted(all_months):
        month_key = f"{year}-{month:02d}"
        monthly_breakdown[month_key] = {
            "revenue": monthly_revenue.get((year, month), 0),
            "expenses": monthly_expenses.get((year, month), 0)
        }
    
    result = {
        "summary": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses
            },
        "by_month": monthly_breakdown
    }
    return result


@tool
def categorize_transactions() -> dict:
    """
    Catégorise automatiquement les transactions par catégorie et par mois :
    Permet d'identifier les variations de dépenses et les mois problématiques.
    
    Catégories : Alimentation, Transport, Logement, Loisirs, Santé, 
                 Frais bancaires, Salaire, Autres


    Utilise cette fonction  pour :
    - "Combien je dépense en une CATÉGORIE spécifique ?"
    - "Où va mon argent ?"
    - Questions sur une CATÉGORIE spécifique          
    
    Returns:
        Dict avec breakdown mensuel : 
        {"2025-01": {"Alimentation": -85.50, ...},
         "2025-02": {...},
         ...}
    """
    import json
    import re

    global df
    # Catégories possibles
    categories = ["Alimentation", "Transport", "Logement", "Loisirs", 
                  "Santé", "Salaire", "Frais bancaires", "Autres"] 
    all_categories = []
    i =  0
    while i < len(df):
        #1. Extraire les libellés à catégoriser
        batch = df[i: i+20]
        batch_indices = list(batch.index)

        # Préparer le prompt
        transactions_text = ""
        for idx, row in batch.iterrows():
            transactions_text += f"{idx} . {row['operation']}\n"
            
        prompt = f"""Catégorise ces transactions bancaires. 
        
        Catégories possibles : {', '.join(categories)}
        Transactions :
        {transactions_text}
        
        Réponds UNIQUEMENT avec une liste JSON au format :
        [{{"index": 0, "category": "..."}}, {{"index": 1, "category": "..."}}, ...]
        """
        #2. Appeler le LLM par batch
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke([{"role": "user", "content": prompt}])
        
        # 3. Parser la réponse du LLM, # Récupérer les catégories assignées
        text = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        #llm_categories = [item['category'] for item in data]
        # ✔️ Recalage fiable des catégories par index réel
        cats_for_batch = [""] * len(batch_indices)
        for item in data:
            idx = item["index"]
            pos = batch_indices.index(idx)
            cats_for_batch[pos] = item["category"]

        # Ajout dans la liste globale
        #all_categories.extend(llm_categories)
        all_categories.extend(cats_for_batch)


        i += 20

    #Ajouter une colonne 'category' au DataFrame
    df['category'] = all_categories
    # 5. Groupby et calculer totaux
    total_by_category = df.groupby('category')['montant'].sum().to_dict()

    monthly_by_category = {}
    
    for (year, month), group in df.groupby([df['date_operation'].dt.year, 
                                             df['date_operation'].dt.month]):
        month_key = f"{year}-{month:02d}"
        monthly_by_category[month_key] = group.groupby('category')['montant'].sum().to_dict()
    
    return {
        "total": total_by_category,
        "by_month": monthly_by_category
    }
    

def predict_monthly_expenses(revenue_input: float) -> float:
    """
    Prédit les dépenses mensuelles basées sur le revenu prévu.
    
    Args:
        revenue_input: Revenu mensuel prévu
        
    Returns:
        Montant des dépenses prédites
    """
    import numpy as np

    global df
    df["date_operation"] = pd.to_datetime(df["date_operation"])

    # Créer une colonne mois au format YYYY-MM
    df["month"] = df["date_operation"].dt.to_period("M")

    # Calculer les revenus et dépenses par mois
    monthly_summary = df.groupby("month")["montant"].agg(
    total_expenses=lambda x: abs(x[x < 0].sum()),
    total_revenue=lambda x: x[x > 0].sum()
    ).reset_index()
    # X et y
    X = monthly_summary[["total_revenue"]]  # Feature : revenus
    y = monthly_summary["total_expenses"]   # Target : dépenses
    
    model = LinearRegression()
    model.fit(X, y)

    revenue_input = pd.DataFrame([[revenue_input]], columns=["total_revenue"])
    predicted_expenses = model.predict(revenue_input)[0]
    print(predicted_expenses)
    #return predicted_expenses
    
    
@tool
def detect_spending_patterns() -> dict:
    """
    Détecte automatiquement les PATTERNS et COMPORTEMENTS cachés dans les dépenses.
    Analyse les comportements par jour, semaine, et identifie les anomalies.

    
    Utilise cette fonction pour :
    - Obtenir un résumé financier de toute la période avec des patterns
    - analyse mes dépenses sur toute la période pour détecter des pattern
    - "Quel jour je dépense le plus ?"
    - "Y a-t-il des dépenses inhabituelles ?"
    - "Quels sont mes patterns de dépenses ?"
    - Combien représente les petites dépenses


    Returns:
        dict: Statistiques agrégées que l'agent IA interprétera intelligemment
    """
    global df
    
    # 1. Prendre uniquement les dépenses 
    expenses = df[df['montant'] < 0].copy()
    if len(expenses) == 0:
        return {"error": "Aucune dépense trouvée dans les données"}
    
    # 2. Ajout colonnes temporelles
    expenses['montant_abs'] = expenses['montant'].abs()
    expenses['day'] = expenses['date_operation'].dt.day_name()
    expenses['month'] = expenses['date_operation'].dt.to_period('M').astype(str)
    #expenses['semaine'] = expenses['date_operation'].dt.isocalendar().week
    nb_months = expenses['date_operation'].dt.to_period('M').nunique()
    
    # 3. Aagrégations de base (jour, mois, type d'opération)
    
    by_day = expenses.groupby('day')['montant_abs'].agg(['sum', 'count']).to_dict('index')
    by_month = expenses.groupby('month')['montant_abs'].sum().to_dict()
    by_type = expenses.groupby('type')['montant_abs'].agg(['sum', 'count']).to_dict('index')

    # Micro-transactions (<5€)
    micro_txs = expenses[expenses['montant_abs'] < 5]
    micro_stats = {
        "count": len(micro_txs),
        "total": float(micro_txs['montant_abs'].sum()),
        "percentage_of_total": float((micro_txs['montant_abs'].sum() / expenses['montant_abs'].sum()) * 100)
    }
    # Transactions importantes (>100€)
    large_txs = expenses[expenses['montant_abs'] > 100]
    large_stats = {
        "count": len(large_txs),
        "total": float(large_txs['montant_abs'].sum()),
        "percentage_of_total": float((large_txs['montant_abs'].sum() / expenses['montant_abs'].sum()) * 100)
    }
    

    # Statistiques globales
    total_spent = float(expenses['montant_abs'].sum())
    total_transactions = len(expenses)
    
    # 4. Retourner les stats pour l'IA 
    return {
        "periode": {
            "debut": expenses['date_operation'].min().strftime('%Y-%m-%d'),
            "fin": expenses['date_operation'].max().strftime('%Y-%m-%d'),
            "nombre_jours": (expenses['date_operation'].max() - expenses['date_operation'].min()).days,
            "nombre_mois": int(nb_months)
        },
        "statistiques_globales": {
            "total_depense": total_spent,
            "nombre_transactions": total_transactions,
        },
        "par_jour_semaine": by_day,
        "par_mois": by_month,
        "par_type_operation": by_type,
        "micro_transactions": micro_stats,
        "grosses_transactions": large_stats,                       
    }



def main():
    global df

    # 1. load data
    df = load_and_clean_data('data/data.xls')
    #df = df[df['montant'] != 0]
   
    # 2. agent
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [analyze_transactions, detect_spending_patterns] #categorize_transactions
    # Prompt système
    prompt = ChatPromptTemplate.from_messages([
    ("system", prompts.PROMPT_BEST), 
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent = agent, tools= tools) #, verbose=True

    # 3. agent ready to bu used
    return agent_executor

    
if __name__ == "__main__":
    #initialize agent
    agent = main()
    print("Agent financier prêt ! Tapez 'quit' pour quitter.\n")
    
    # Boucle interactive
    while True:
        user_input = input("Vous : ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Au revoir !")
            break
        
        response = agent.invoke({"input": user_input})
        print(f"\nAgent : {response['output']}\n")
