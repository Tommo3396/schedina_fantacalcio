import pandas as pd
import streamlit as st

# Funzione per caricare i dati dal file Excel
def load_data_from_excel(file_path):
    # Dizionario per le squadre
    teams = {}
    excel_file = pd.ExcelFile(file_path)
    
    # Caricare i punteggi recenti
    recent_scores_df = excel_file.parse('RecentScores')
    
    # Caricare la classifica
    standings_df = excel_file.parse('Classifica')
    standings = {row['Team']: row['Position'] for _, row in standings_df.iterrows()}
    
    # Caricare le partite di Fantacalcio
    fanta_matches_df = excel_file.parse('FantaNextMatch')
    fantacalcio_matches = [(row['Team1'], row['Team2']) for _, row in fanta_matches_df.iterrows()]
    
    # Caricare le partite di Serie A
    serie_a_matches_df = excel_file.parse('SerieANextMatch')
    serie_a_fixtures = [{"home": row['Home'], "away": row['Away']} for _, row in serie_a_matches_df.iterrows()]
    
    # Caricare i dettagli delle squadre
    for team_name in excel_file.sheet_names:
        if team_name in ['RecentScores', 'Classifica', 'FantaNextMatch', 'SerieANextMatch']:
            continue  # Salta i fogli predefiniti
        sheet = excel_file.parse(team_name)
        players = [
            {"name": row['name'], "team": row['team']}
            for _, row in sheet.iterrows() if row.get('selected') == 'X'
        ]
        recent_scores = recent_scores_df[team_name].tolist()
        
        teams[team_name] = {"players": players, "recent_scores": recent_scores}
    
    return teams, standings, fantacalcio_matches, serie_a_fixtures

# Funzione per calcolare il punteggio medio
def calculate_team_average(team):
    return sum(fantacalcio_teams[team]["recent_scores"]) / len(fantacalcio_teams[team]["recent_scores"])

# Funzione per convertire il punteggio in gol
def calculate_goals(score):
    if score < 66:
        return 0
    elif score < 72:
        return 1
    else:
        return 2 + (score - 72) // 4

# Funzione per calcolare l'impatto della classifica
def standings_impact(team):
    position = fantacalcio_standings.get(team, float('inf'))
    return max(0.95, 1.05 - 0.01 * (position - 1))

# Funzione per calcolare l'impatto della difficoltà
def fixture_difficulty_impact(team):
    players = fantacalcio_teams[team]["players"]
    difficulty_factor = 1.0
    for player in players:
        player_team = player["team"]
        for match in serie_a_fixtures:
            if match["home"] == player_team or match["away"] == player_team:
                opponent = match["away"] if match["home"] == player_team else match["home"]
                if opponent in ["Napoli", "Juventus", "Inter"]:
                    difficulty_factor *= 0.992
                elif opponent in ["Milan", "Roma", "Lazio", "Fiorentina", "Atalanta"]:
                    difficulty_factor *= 0.995
                elif opponent in ["Udinese", "Empoli", "Torino"]:
                    difficulty_factor *= 0.998
                elif opponent in ["Bologna", "Verona", "Como"]:
                    difficulty_factor *= 1.001
                elif opponent in ["Cagliari", "Monza", "Parma"]:
                    difficulty_factor *= 1.005
                else:
                    difficulty_factor *= 1.008
    return difficulty_factor

def calculate_match_probabilities(avg_score_team1, avg_score_team2):
    # Definizione delle soglie gol
    score_thresholds = [66, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112]
    
 # Calcolo della distanza tra i punteggi medi
    score_diff = abs(avg_score_team1 - avg_score_team2)
    
    # Calcolo iniziale delle probabilità
    base_prob = 50  # Probabilità base di vittoria per entrambe le squadre
    prob_draw = 0
    
    # Calcolo dinamico della probabilità di pareggio
    # Utilizziamo una funzione logaritmica per modellare il cambiamento nella probabilità di pareggio
    if score_diff == 0:
        prob_draw = 40  # Massima probabilità di pareggio quando i punteggi sono uguali
    else:
        # La probabilità di pareggio diminuisce con l'aumentare della differenza
        prob_draw = max(0, 40 - (score_diff * 2))  # Riduce di 2% per ogni punto di differenza

    # Determinazione delle probabilità di vittoria in base ai punteggi medi
    prob_win_team1 = max(0, 38 + ((avg_score_team1 - avg_score_team2) * 2))
    prob_win_team2 = max(0, 37 + ((avg_score_team2 - avg_score_team1) * 2))
    print("")
    print(prob_win_team1)
    print(prob_win_team2)
    print(prob_draw)
    print("")
    # Normalizzazione
    total_prob = prob_win_team1 + prob_win_team2 + prob_draw
    prob_win_team1 = (prob_win_team1 / total_prob) * 100
    prob_draw = (prob_draw / total_prob) * 100
    prob_win_team2 = (prob_win_team2 / total_prob) * 100

    return prob_win_team1, prob_draw, prob_win_team2

# Funzione per calcolare le probabilità con un totale del 95%
def calculate_probabilities(team1, team2, is_home_team1):
    avg_team1 = calculate_team_average(team1) * standings_impact(team1) * fixture_difficulty_impact(team1)
    avg_team2 = calculate_team_average(team2) * standings_impact(team2) * fixture_difficulty_impact(team2)

    if home_advantage and is_home_team1:
        avg_team1 += 1
    elif home_advantage and not is_home_team1:
        avg_team2 += 1
    
    odds_team1, odds_draw, odds_team2 = calculate_match_probabilities(avg_team1, avg_team2)

    return odds_team1, odds_draw, odds_team2
    
# Funzione per calcolare le quote
def calculate_odds(prob):
    return round(100 / prob, 2) if prob > 0 else float('inf')

# Generazione delle quote per le partite di Fantacalcio
def generate_odds_for_matches():
    odds = {}
    for match in fantacalcio_matches:
        team1, team2 = match
        prob_win_team1, prob_draw, prob_win_team2 = calculate_probabilities(team1, team2, is_home_team1=True)
        odds[match] = {
            "Win Team 1": calculate_odds(prob_win_team1),
            "Draw": calculate_odds(prob_draw),
            "Win Team 2": calculate_odds(prob_win_team2)
        }
    return odds

# Caricamento del file Excel
file_path = 'fantacalcio_teams.xlsx'
fantacalcio_teams, fantacalcio_standings, fantacalcio_matches, serie_a_fixtures = load_data_from_excel(file_path)
home_advantage = True  # Variabile di vantaggio casa

# Costruire la tabella delle quote
odds_for_matches = generate_odds_for_matches()
matches_data = []
for match, odds in odds_for_matches.items():
    match_info = {
        "Partita": f"{match[0]} - {match[1]}",
        "Quota 1": odds["Win Team 1"],
        "Quota X": odds["Draw"],
        "Quota 2": odds["Win Team 2"]
    }
    matches_data.append(match_info)

matches_df = pd.DataFrame(matches_data)

# Interfaccia Streamlit
st.title("Partite Fantacalcio")
st.write("Seleziona l'esito di ogni partita:")

# Aggiungere una colonna per la selezione del risultato tramite select box
selections = []
for i in range(len(matches_df)):
    st.write(f"**{matches_df['Partita'][i]}**")
    selections.append(st.radio(
        "Esito",
        options=["1", "X", "2"],
        format_func=lambda x: f"{x} ({matches_df[f'Quota {x}'][i]})" if x in ["1", "X", "2"] else "Seleziona",
        key=f"select_{i}"
    ))

# Aggiorna il DataFrame con le selezioni
matches_df['Esito Selezionato'] = selections

# Calcolo della quota totale
total_odds = 1.0
for i in range(len(matches_df)):
    if matches_df['Esito Selezionato'][i] == "1":
        total_odds *= matches_df['Quota 1'][i]
    elif matches_df['Esito Selezionato'][i] == "X":
        total_odds *= matches_df['Quota X'][i]
    elif matches_df['Esito Selezionato'][i] == "2":
        total_odds *= matches_df['Quota 2'][i]

st.write("**Quota Totale**:", round(total_odds, 2))

# Campo per l'importo giocato
importo_giocato = st.number_input("Importo giocato (solo numeri interi)", min_value=1, step=1)

# Calcolo della vincita potenziale
vincita_potenziale = importo_giocato * total_odds
st.write("**Vincita Potenziale**:", round(vincita_potenziale, 2))
