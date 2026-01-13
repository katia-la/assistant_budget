from core import tools
from core.agent import create_agent
from core.data_loader import load_and_clean_data

    
if __name__ == "__main__":
    # 1. load data
    df = load_and_clean_data('data/data.xls')
    tools.df = df
    
    #initialize agent
    agent = create_agent()
    print("Agent financier prêt ! Tapez 'quit' pour quitter.\n")
    
    # Boucle interactive
    while True:
        user_input = input("Vous : ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Au revoir !")
            break
        
        response = agent.invoke({"input": user_input})
        print(f"\nAgent : {response['output']}\n")