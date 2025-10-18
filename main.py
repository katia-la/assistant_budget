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

def analyze_transactions_wothouttool(df) -> dict:  # fonction normale, pas @tool
    """
    Analyse les transactions bancaires et retourne:

    - Total des revenus et dépenses
    - Breakdown mensuel des revenus et dépenses
    
    Args:
        df: DataFrame avec colonnes date_operation, type, operation, montant
    Returns:
        Dict avec summary (totaux) et by_month (détail mensuel)
    """
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


def main():
    global df

    # 1. load data
    df = load_and_clean_data('data/data.xls')
    print('avec tools ...')
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [analyze_transactions]
    # Prompt système
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Tu es un assistant financier expert qui aide les utilisateurs 
        à analyser leurs transactions bancaires. Tu es pédagogue, précis et tu donnes 
        des conseils pratiques basés sur les données.
        
        Quand tu reçois les résultats d'analyse, présente-les de façon claire et 
        donne des insights pertinents (tendances, mois problématiques, recommandations)."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent = agent, tools= tools)
    #analyze_transactions(df)
    # Test l'agent
    response = agent_executor.invoke({
        "input": "Analyse mes transactions et dis-moi comment je gère mon budget"
    })

    print(response['output'])


if __name__ == "__main__":
    main()
