import pandas as pd
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import  AgentExecutor, create_tool_calling_agent #tool_calling_agent
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
    Analyse les transactions bancaires et retourne:

    - Total des revenus et dépenses
    - Breakdown mensuel des revenus et dépenses
    

    Returns:
        Dict avec summary (totaux) et by_month (détail mensuel)
    """
    global df 
    total_revenue = df[df['montant']>0]['montant'].sum()
    total_expenses = df[df['montant']<0]['montant'].sum()

    # Group by année ET mois
    monthly_revenue = df[df['montant']>0].groupby([
        df['date_operation'].dt.year,
        df['date_operation'].dt.month
    ])['montant'].sum().to_dict()

    monthly_expenses = df[df['montant']<0].groupby([
        df['date_operation'].dt.year,
        df['date_operation'].dt.month
    ])['montant'].sum().to_dict()

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
        llm_categories = [item['category'] for item in data]
        all_categories.extend(llm_categories)

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
    


def main():
    global df

    # 1. load data
    df = load_and_clean_data('data/data.xls')
    print('avec tools ...')
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [analyze_transactions, categorize_transactions]
    # Prompt système
    prompt = ChatPromptTemplate.from_messages([
    ("system", """Tu es un assistant financier expert qui aide les utilisateurs 
    à analyser leurs transactions bancaires. Tu es pédagogue, précis et tu donnes 
    des conseils pratiques basés sur les données.
    
    IMPORTANT : 
    - Tu dois UNIQUEMENT utiliser les données fournies par les tools
    - Si un mois n'est pas dans les données, dis-le clairement à l'utilisateur
    - N'INVENTE JAMAIS de chiffres ou d'analyses sur des données inexistantes
    - Vérifie toujours la période couverte par les données avant de répondre
    
    Quand tu reçois les résultats d'analyse, présente-les de façon claire et 
    donne des insights pertinents (tendances, mois problématiques, recommandations)."""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent = agent, tools= tools)

    # Test 1 
    #response = agent_executor.invoke({
    #    "input": "Analyse mes transactions et dis-moi comment je gère mon budget"
    #})

    #print(response['output'])
    
    #Test 2
    print("Test 2: \n")
    response = agent_executor.invoke({
        "input": "Catégorise mes dépenses par mois et dis-moi où je dépense le plus"
    })
    print(response['output'])

if __name__ == "__main__":
    main()
