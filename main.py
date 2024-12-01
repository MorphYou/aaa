import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
from PIL import Image, ImageTk
import requests
from io import BytesIO
import datetime
import os
from typing import Dict, List, Optional

# Jedna klasa w programie do obsługi API
class RiotAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-Riot-Token": self.api_key
        }

    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
        """Pobiera dane konta na podstawie Riot ID"""
        regions = ["europe", "americas", "asia", "sea"]
        
        for region in regions:
            url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"Błąd podczas pobierania danych konta: {e}")
                continue
        return None

    def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict]:
        """Pobiera dane przywoływacza po PUUID"""
        regions = ["eun1", "euw1", "na1", "kr", "br1", "jp1", "la1", "la2", "oc1", "tr1", "ru"]
        
        for region in regions:
            url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        return None

    def get_ranked_stats(self, summoner_id: str) -> Optional[List[Dict]]:
        """Pobiera statystyki rankingowe"""
        url = f"https://eun1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_match_history(self, puuid: str, count: int = 20) -> Optional[List[str]]:
        """Pobiera historię meczy"""
        url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """Pobiera szczegóły meczu"""
        url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_champion_mastery(self, puuid: str) -> Optional[List[Dict]]:
        """Pobiera top championów gracza"""
        url = f"https://eun1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_player_data(self, riot_id: str) -> Dict:
        """Pobiera wszystkie dane gracza"""
        try:
            if '#' in riot_id:
                game_name, tag_line = riot_id.split('#')
            else:
                game_name = riot_id
                tag_line = 'EUW'

            # Pobierz dane konta
            account_data = self.get_account_by_riot_id(game_name, tag_line)
            if not account_data:
                return None

            puuid = account_data.get('puuid')
            if not puuid:
                return None

            # Pobierz pozostałe dane
            summoner_data = self.get_summoner_by_puuid(puuid)
            matches_data = self.get_match_history_details(puuid)
            ranked_stats = self.get_ranked_stats(summoner_data.get('id')) if summoner_data else None
            champion_mastery = self.get_champion_mastery(puuid)

            # Przetwórz dane
            if summoner_data:
                summoner_data['gameName'] = account_data.get('gameName')
                summoner_data['tagLine'] = account_data.get('tagLine')

            processed_data = self.process_summoner_data(summoner_data, matches_data)

            return {
                "account_data": account_data,
                "summoner_data": processed_data,
                "ranked_stats": ranked_stats or [],
                "matches_data": matches_data,
                "champion_mastery": champion_mastery or []
            }

        except Exception as e:
            print(f"Błąd podczas pobierania danych gracza: {e}")
            return None

    def get_match_history_details(self, puuid: str) -> List[Dict]:
        """Pobiera szczegółowe dane meczy"""
        matches_data = []
        match_ids = self.get_match_history(puuid, 20)
        
        if match_ids:
            for match_id in match_ids:
                match_details = self.get_match_details(match_id)
                if match_details:
                    matches_data.append(match_details)
        
        return matches_data

    def process_summoner_data(self, summoner_data: Dict, matches_data: List[Dict]) -> Dict:
        """Przetwarza dane przywoływacza"""
        if not summoner_data:
            return None

        avg_stats = self.calculate_average_stats(matches_data, summoner_data.get('puuid', ''))
        top_champions = self.calculate_champion_stats(matches_data, summoner_data.get('puuid', ''))

        return {
            'name': summoner_data.get('gameName', summoner_data.get('name', 'Unknown')),
            'level': summoner_data.get('summonerLevel', 0),
            'icon_id': summoner_data.get('profileIconId', 1),
            'avg_stats': avg_stats,
            'top_champions': top_champions,
            'puuid': summoner_data.get('puuid', '')
        }

    def calculate_average_stats(self, matches_data: List[Dict], puuid: str) -> Dict:
        """Oblicza średnie statystyki z meczy"""
        if not matches_data:
            return {
                'kda': '0/0/0',
                'cs_per_min': 0,
                'damage_per_min': 0,
                'vision_score': 0,
                'total_games': 0,
                'wins': 0
            }

        total_kills = total_deaths = total_assists = 0
        total_cs = total_damage = total_vision_score = total_game_duration = 0
        wins = valid_games = 0

        for match in matches_data:
            try:
                player_data = next((p for p in match['info']['participants'] 
                                  if p['puuid'] == puuid), None)
                if not player_data:
                    continue

                game_duration = match['info']['gameDuration'] / 60
                
                total_kills += player_data['kills']
                total_deaths += player_data['deaths']
                total_assists += player_data['assists']
                total_cs += player_data['totalMinionsKilled'] + player_data['neutralMinionsKilled']
                total_damage += player_data['totalDamageDealtToChampions']
                total_vision_score += player_data['visionScore']
                total_game_duration += game_duration

                if player_data['win']:
                    wins += 1

                valid_games += 1

            except Exception as e:
                print(f"Błąd podczas przetwarzania meczu: {e}")
                continue

        if valid_games == 0:
            return {
                'kda': '0/0/0',
                'cs_per_min': 0,
                'damage_per_min': 0,
                'vision_score': 0,
                'total_games': 0,
                'wins': 0
            }

        avg_deaths = total_deaths / valid_games
        kda = f"{total_kills/valid_games:.1f}/{avg_deaths:.1f}/{total_assists/valid_games:.1f}"
        
        return {
            'kda': kda,
            'cs_per_min': round(total_cs / total_game_duration, 1),
            'damage_per_min': round(total_damage / total_game_duration, 1),
            'vision_score': round(total_vision_score / valid_games, 1),
            'total_games': valid_games,
            'wins': wins,
            'winrate': round((wins / valid_games * 100), 1) if valid_games > 0 else 0
        }

    def calculate_champion_stats(self, matches_data: List[Dict], puuid: str) -> List[Dict]:
        """Oblicza statystyki championów"""
        champion_stats = {}
        
        for match in matches_data:
            try:
                player_data = next((p for p in match['info']['participants'] 
                                  if p['puuid'] == puuid), None)
                if not player_data:
                    continue
                
                champion_name = player_data['championName']
                if champion_name not in champion_stats:
                    champion_stats[champion_name] = {
                        'games': 0,
                        'wins': 0,
                        'kills': 0,
                        'deaths': 0,
                        'assists': 0
                    }
                
                stats = champion_stats[champion_name]
                stats['games'] += 1
                if player_data['win']:
                    stats['wins'] += 1
                stats['kills'] += player_data['kills']
                stats['deaths'] += player_data['deaths']
                stats['assists'] += player_data['assists']
                
            except Exception as e:
                print(f"Błąd podczas obliczania statystyk championa: {e}")
                continue
        
        champions_list = []
        for champ, stats in champion_stats.items():
            winrate = (stats['wins'] / stats['games']) * 100 if stats['games'] > 0 else 0
            avg_kda = ((stats['kills'] + stats['assists']) / stats['deaths']) if stats['deaths'] > 0 else (stats['kills'] + stats['assists'])
            
            champions_list.append({
                'name': champ,
                'games': stats['games'],
                'winrate': winrate,
                'avg_kda': avg_kda,
                'kills': stats['kills'],
                'deaths': stats['deaths'],
                'assists': stats['assists']
            })
        
        champions_list.sort(key=lambda x: (x['games'], x['winrate']), reverse=True)
        return champions_list[:5]

# Fukncje przeniesione w jedno miejsce dla czytelności kodu

def zamknij_okno():
    root.destroy()

def saveLastClick(event):
    global lastClickX, lastClickY
    lastClickX = event.x
    lastClickY = event.y

def drag(event):
    x, y = event.x - lastClickX + root.winfo_x(), event.y - lastClickY + root.winfo_y()
    root.geometry(f"+{x}+{y}")

def calculate_winrate(ranked_data):
    total_games = ranked_data['wins'] + ranked_data['losses']
    if total_games == 0:
        return 0
    return round((ranked_data['wins'] / total_games) * 100, 1)

def load_champion_icon(champion_id):
    try:
        filepath = f"assets/champions/{champion_id}.png"
        img = Image.open(filepath)
        img = img.resize((40, 40), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Błąd ładowania ikony championa: {e}")
        return None

def load_rank_icon(tier):
    try:
        filepath = f"assets/ranks/{tier.lower()}.png"
        img = Image.open(filepath)
        img = img.resize((128, 128), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Błąd ładowania ikony rangi: {e}")
        return None

def load_item_icon(item_id):
    """Ładuje ikonę przedmiotu z API Riot Games"""
    try:
        # Ikon przedmiotów może być dużo więc użyłem cache do przyśpieszenia ładowania
        if not hasattr(load_item_icon, 'cache'):
            load_item_icon.cache = {}

        if item_id in load_item_icon.cache:
            return load_item_icon.cache[item_id]

        filepath = f"assets/items/{item_id}.png"
        img = Image.open(filepath)
        img = img.resize((30, 30), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        load_item_icon.cache[item_id] = photo
        return photo
    except Exception as e:
        print(f"Błąd podczas ładowania ikony przedmiotu {item_id}: {e}")
        return None

def load_profile_icon(icon_id):
    try:
        url = f"http://ddragon.leagueoflegends.com/cdn/13.24.1/img/profileicon/{icon_id}.png"
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img = img.resize((128, 128), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Błąd ładowania ikony profilu: {e}")
        return None

def load_summoner_spell_icon(spell_id):
    """Ładuje ikonę czaru przywoływacza"""
    spell_path = os.path.join('assets', 'summoner_spells', f"{spell_id}.png")
    if os.path.exists(spell_path):
        try:
            image = Image.open(spell_path)
            image = image.resize((24, 24), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"Błąd podczas ładowania ikony czaru {spell_id}: {e}")
    return None

def get_queue_type(queue_id):
    queue_types = {
        400: "Normal",
        420: "Ranked Solo",
        430: "Normal",
        440: "Ranked Flex",
        450: "ARAM",
        700: "Clash",
        830: "Co-op vs AI",
        840: "Co-op vs AI",
        850: "Co-op vs AI",
        900: "URF",
        1020: "One for All",
        1300: "Nexus Blitz",
        1400: "Ultimate Spellbook",
        1700: "Arena",
    }
    return queue_types.get(queue_id, "Other")

def update_match_history(matches_data, puuid):
    try:
        for widget in match_history_panel.winfo_children():
            widget.destroy()

        match_canvas.yview_moveto(0)

        for match in matches_data:
            try:
                player_data = next((p for p in match['info']['participants'] 
                                  if p['puuid'] == puuid), None)
                if not player_data:
                    continue
                
                match_frame = ttk.Frame(match_history_panel, style="Match.TFrame", cursor="hand2")
                match_frame.pack(fill=X, padx=5, pady=2)
                match_frame.grid_columnconfigure(1, weight=1)

                champion_frame = ttk.Frame(match_frame)
                champion_frame.grid(row=0, column=0, padx=(5,0), pady=5)

                champion_name = player_data.get('championName', 'Unknown')
                champion_icon = load_champion_icon(champion_name)
                if champion_icon:
                    champ_label = ttk.Label(champion_frame, image=champion_icon)
                    champ_label.image = champion_icon
                    champ_label.pack()

                stats_frame = ttk.Frame(match_frame)
                stats_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

                result_text = "Wygrana" if player_data.get('win') else "Przegrana"
                result_color = "#4CAF50" if player_data.get('win') else "#F44336"
                queue_type = get_queue_type(match['info'].get('queueId', 0))
                
                top_row = ttk.Frame(stats_frame)
                top_row.pack(fill=X)
                
                # Nazwa championa ma ograniczoną szerokość coś mi to psuło
                champ_name_label = ttk.Label(top_row, 
                                           text=champion_name,
                                           font=("Helvetica", 10, "bold"),
                                           width=12)
                champ_name_label.pack(side=LEFT)

                result_label = ttk.Label(top_row,
                         text=f"{result_text} - {queue_type}",
                         font=("Helvetica", 10, "bold"),
                         foreground=result_color)
                result_label.pack(side=LEFT)

                kills = player_data.get('kills', 0)
                deaths = player_data.get('deaths', 0)
                assists = player_data.get('assists', 0)
                kda = f"KDA: {kills}/{deaths}/{assists}"
                ttk.Label(stats_frame, text=kda).pack(anchor=W)

                cs = player_data.get('totalMinionsKilled', 0) + player_data.get('neutralMinionsKilled', 0)
                gold = player_data.get('goldEarned', 0)
                cs_gold = f"CS: {cs} | Gold: {gold:,}"
                ttk.Label(stats_frame, text=cs_gold).pack(anchor=W)

                items_frame = ttk.Frame(match_frame)
                items_frame.grid(row=0, column=2, padx=5, pady=5)

                item_slots = [player_data.get(f'item{i}', 0) for i in range(7)]

                # ....... tu był mega problem
                for i, item_id in enumerate(item_slots[:-1]):
                    row = i // 3
                    col = i % 3
                    if item_id > 0:
                        item_icon = load_item_icon(item_id)
                        if item_icon:
                            item_label = ttk.Label(items_frame, image=item_icon)
                            item_label.image = item_icon
                            item_label.grid(row=row, column=col, padx=1, pady=1)
                    else:
                        empty_slot = ttk.Label(items_frame, width=2)
                        empty_slot.grid(row=row, column=col, padx=1, pady=1)

                # XD
                trinket_id = item_slots[-1]
                if trinket_id > 0:
                    trinket_icon = load_item_icon(trinket_id)
                    if trinket_icon:
                        trinket_label = ttk.Label(items_frame, image=trinket_icon)
                        trinket_label.image = trinket_icon
                        trinket_label.grid(row=0, column=3, rowspan=2, padx=(5,1), pady=1)

            except Exception as e:
                print(f"Błąd podczas aktualizacji meczu: {e}")
                continue

        # Tu też coś mi psuło
        match_canvas.update_idletasks()
        match_canvas.configure(scrollregion=match_canvas.bbox("all"))

    except Exception as e:
        print(f"Błąd podczas aktualizacji historii meczy: {e}")

def update_champion_stats(champion_data):
    sorted_champions = sorted(champion_data, 
                            key=lambda x: (x['games'], x['winrate']), 
                            reverse=True)[:5]
    
    for i, (champ_frame, champ_data) in enumerate(zip(top_champs_container.winfo_children(), sorted_champions)):
        champ_icon_frame = champ_frame.winfo_children()[0]
        champ_icon_label = champ_icon_frame.winfo_children()[0]
        champ_info_frame = champ_frame.winfo_children()[1]
        champ_name_label = champ_info_frame.winfo_children()[0]
        champ_stats_label = champ_info_frame.winfo_children()[1]

        champion_icon = load_champion_icon(champ_data['name'])
        if champion_icon:
            champ_icon_label.configure(image=champion_icon)
            champ_icon_label.image = champion_icon

        champ_name_label.configure(text=champ_data['name'])
        stats_text = f"{champ_data['games']} gier | {champ_data['winrate']:.1f}% WR | KDA: {champ_data['avg_kda']:.1f}"
        champ_stats_label.configure(text=stats_text)

def update_ui(player_data):
    try:
        summoner_data = player_data.get('summoner_data', {})
        if not summoner_data:
            show_error_message("Nie znaleziono danych gracza")
            return

        profile_icon_id = summoner_data.get('profileIconId', 1)
        profile_icon = load_profile_icon(profile_icon_id)
        if profile_icon:
            avatar_label.configure(image=profile_icon)
            avatar_label.image = profile_icon
        nickname_label.configure(text=summoner_data.get('name', 'Nieznany'))
        level_label.configure(text=f"Poziom: {summoner_data.get('level', 0)}")

        avg_stats = summoner_data.get('avg_stats', {})
        
        # Tuteż trochę spędziłem
        kda_value.config(text=avg_stats.get('kda', '0/0/0'))
        cs_value.config(text=f"{avg_stats.get('cs_per_min', 0):.1f}")
        dpm = avg_stats.get('damage_per_min', 0)
        dpm_text = f"{dpm/1000:.1f}k" if dpm >= 1000 else f"{dpm:.0f}"
        dpm_value.config(text=dpm_text)
        ward_value.config(text=f"{avg_stats.get('vision_score', 0):.1f}")

        total_games = avg_stats.get('total_games', 0)
        wins = avg_stats.get('wins', 0)
        winrate = (wins / total_games * 100) if total_games > 0 else 0
        games_info = f"W/L: {wins}/{total_games-wins} ({winrate:.1f}%)"
        games_label.config(text=games_info)

        matches_data = player_data.get('matches_data', [])
        update_match_history(matches_data, summoner_data.get('puuid'))

        top_champions = summoner_data.get('top_champions', [])
        update_champion_stats(top_champions)

        ranked_stats = player_data.get('ranked_stats', [])
        if ranked_stats:
            solo_queue = next((queue for queue in ranked_stats 
                             if queue['queueType'] == 'RANKED_SOLO_5x5'), None)
            if solo_queue:
                tier = solo_queue.get('tier', 'UNRANKED')
                rank = solo_queue.get('rank', '')
                lp = solo_queue.get('leaguePoints', 0)
                wins = solo_queue.get('wins', 0)
                losses = solo_queue.get('losses', 0)
                total_games = wins + losses
                winrate = (wins / total_games * 100) if total_games > 0 else 0

                rank_icon = load_rank_icon(tier)
                if rank_icon:
                    rank_icon_label.configure(image=rank_icon)
                    rank_icon_label.image = rank_icon

                rank_name.config(text=f"{tier} {rank}")
                winrate_label.config(text=f"Winrate: {winrate:.1f}%")
                lp_value.config(text=str(lp))
            else:
                # !!!!!!
                rank_icon_label.configure(image='')
                rank_name.config(text="Unranked")
                winrate_label.config(text="Winrate: 0%")
                lp_value.config(text="0")
    
    except Exception as e:
        print(f"Błąd podczas aktualizacji interfejsu: {e}")
        show_error_message("Wystąpił błąd podczas aktualizacji interfejsu")

def show_error_message(message):
    error_window = ttk.Toplevel()
    error_window.title("Błąd")
    error_window.geometry("300x100")
    
    label = ttk.Label(error_window, text=message, wraplength=250)
    label.pack(padx=20, pady=20)
    
    ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy)
    ok_button.pack(pady=10)

def show_loading_window():
    loading_window = ttk.Toplevel()
    loading_window.title("Ładowanie")
    loading_window.geometry("300x150")
    loading_window.transient(root)  # i tu taki zindex
    loading_window.grab_set()  # unterakcja niet

    loading_window.geometry("+%d+%d" % (
        root.winfo_x() + (root.winfo_width() // 2 - 150),
        root.winfo_y() + (root.winfo_height() // 2 - 75)
    ))
    
    label = ttk.Label(loading_window, text="Ładowanie danych gracza...", font=("Helvetica", 10))
    label.pack(pady=20)
    
    progress = ttk.Progressbar(
        loading_window, 
        mode='indeterminate', # !!
        style='info.Striped.Horizontal.TProgressbar'
    )
    progress.pack(padx=20, pady=10, fill=X)
    progress.start(15) 
    
    status_label = ttk.Label(loading_window, text="Łączenie z serwerem...", font=("Helvetica", 9))
    status_label.pack(pady=10)
    
    return loading_window, status_label

def search_player():
    riot_id = search_entry.get()
    if not riot_id:
        show_error_message("Wprowadź nazwę gracza w formacie: nazwa#tag")
        return
 
    loading_window, status_label = show_loading_window()
    
    def update_status(text):
        status_label.config(text=text)
    
    def search_thread():
        try:
            api_key = "RGAPI-a16b915f-274f-4254-8b34-eabd6e5e8fe6"  # API
            riot_api = RiotAPI(api_key)
 
            root.after(0, lambda: update_status("Pobieranie danych gracza..."))
            player_data = riot_api.get_player_data(riot_id)
            
            if player_data:
                root.after(0, lambda: update_status("Aktualizacja interfejsu..."))
                root.after(0, lambda: update_ui(player_data))
                root.after(0, loading_window.destroy)
            else:
                root.after(0, loading_window.destroy)
                root.after(0, lambda: show_error_message("Nie znaleziono gracza. Sprawdź nazwę i spróbuj ponownie."))
        
        except Exception as e:
            root.after(0, loading_window.destroy)
            root.after(0, lambda: show_error_message(f"Wystąpił błąd: {str(e)}"))
            print(f"Szczegóły błędu: {type(e).__name__}")
    
    # Tak jak Pan chciał użycie osobnych wątków aby nie lagowac apki
    thread = threading.Thread(target=search_thread)
    thread.daemon = True
    thread.start()

# tutaj gotowa funkcja przerobiona 
def get_current_lol_version():
    try:
        response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
        response.raise_for_status()
        versions = response.json()
        current_version = versions[0] 
        major, minor = current_version.split('.')[:2]  # bo zwracało sieczkę 
        return major, minor
    except Exception as e:
        print(f"Błąd podczas pobierania wersji: {e}")
        return "14", "24"  # na początku miałem błędy więc użyłem i zostawiłem return w przypadku błędu

def open_patch_notes():
    major, minor = get_current_lol_version()
    url = f"https://www.leagueoflegends.com/pl-pl/news/game-updates/patch-{major}-{minor}-notes/"
    webbrowser.open(url)

# Koniec funkcji
root = ttk.Window(themename="darkly", overrideredirect=TRUE)
root.geometry("1280x800")

style = ttk.Style()
style.configure("MatchHover.TFrame", background="#2a3f5f")

style.configure("PlayerCard.TFrame", background="#2a2a2a")
style.configure("CurrentPlayer.TFrame", background="#1a3d5c")

style.configure("SearchedPlayer.TLabel", 
               font=("Helvetica", 11, "bold"),
               foreground="#00ff99")
style.configure("SearchedPlayerStats.TLabel", 
               font=("Helvetica", 10),
               foreground="#00ff99")

navbar = ttk.Frame(root, style="secondary.TFrame", cursor="hand2")
navbar.pack(side=TOP, fill=X)

navbar.bind("<Button-1>", saveLastClick)
navbar.bind("<B1-Motion>", drag)

home_btn = ttk.Button(navbar, text="Patch Notes", style="secondary.Outline.TButton", command=open_patch_notes)
home_btn.pack(side=LEFT, padx=5, pady=5)

nav_title = ttk.Label(navbar, text="Lol Stats Finder", style="secondary.Inverse.TLabel", font=("Helvetica", 12, "bold"))
nav_title.place(relx=0.5, rely=0.5, anchor="center")

about_btn = ttk.Button(navbar, text="X", style="secondary.Outline.TButton", command=zamknij_okno)
about_btn.pack(side=RIGHT, padx=5, pady=5)

top_section = ttk.Frame(root)
top_section.pack(fill=X, padx=20, pady=10)

player_info_frame = ttk.Frame(top_section)
player_info_frame.pack(side=LEFT, fill=Y, padx=20, pady=20)

player_info_container = ttk.Frame(player_info_frame)
player_info_container.pack(fill=X)

avatar_frame = ttk.Frame(player_info_container, width=128, height=128, style="secondary.TFrame")
avatar_frame.pack(side=LEFT, pady=(0, 10))
avatar_frame.pack_propagate(False)

avatar_label = ttk.Label(avatar_frame)
avatar_label.pack(fill=BOTH, expand=True)

info_text_container = ttk.Frame(player_info_container)
info_text_container.pack(side=LEFT, padx=(10, 0), pady=(0, 10))

nickname_label = ttk.Label(info_text_container, text="Nickname", font=("Helvetica", 16, "bold"))
nickname_label.pack(anchor=W)

level_label = ttk.Label(info_text_container, text="Level: 0")
level_label.pack(anchor=W)

search_frame = ttk.Frame(top_section)
search_frame.pack(side=RIGHT, fill=X, padx=20, pady=20, anchor=E)

search_label = ttk.Label(search_frame, text="Wyszukaj gracza")
search_label.pack(pady=(0, 5))

search_entry = ttk.Entry(search_frame, width=40)
search_entry.pack(side=LEFT, padx=5)

search_button = ttk.Button(search_frame, text="Szukaj", style="primary.TButton", command=search_player)
search_button.pack(side=LEFT, padx=5)

bottom_section = ttk.Frame(root)
bottom_section.pack(fill=BOTH, expand=True, padx=20, pady=10)

stats_container = ttk.Frame(bottom_section)
stats_container.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

left_block = ttk.Frame(stats_container)
left_block.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

stats_panel = ttk.Frame(left_block, style="secondary.TFrame")
stats_panel.pack(fill=X, padx=5, pady=5)

ttk.Label(stats_panel, text="Statystyki", font=("Helvetica", 14, "bold")).pack(pady=5)

kda_frame = ttk.Frame(stats_panel)
kda_frame.pack(fill=X, padx=10, pady=5)
ttk.Label(kda_frame, text="KDA", font=("Helvetica", 12, "bold")).pack(side=LEFT)
kda_value = ttk.Label(kda_frame, text="0/0/0")
kda_value.pack(side=RIGHT)

cs_frame = ttk.Frame(stats_panel)
cs_frame.pack(fill=X, padx=10, pady=5)
ttk.Label(cs_frame, text="CS/min", font=("Helvetica", 12, "bold")).pack(side=LEFT)
cs_value = ttk.Label(cs_frame, text="0")
cs_value.pack(side=RIGHT)

dpm_frame = ttk.Frame(stats_panel)
dpm_frame.pack(fill=X, padx=10, pady=5)
ttk.Label(dpm_frame, text="DPM", font=("Helvetica", 12, "bold")).pack(side=LEFT)
dpm_value = ttk.Label(dpm_frame, text="0")
dpm_value.pack(side=RIGHT)

ward_frame = ttk.Frame(stats_panel)
ward_frame.pack(fill=X, padx=10, pady=5)
ttk.Label(ward_frame, text="Vision", font=("Helvetica", 12, "bold")).pack(side=LEFT)
ward_value = ttk.Label(ward_frame, text="0")
ward_value.pack(side=RIGHT)

games_frame = ttk.Frame(stats_panel)
games_frame.pack(fill=X, padx=10, pady=5)
ttk.Label(games_frame, text="W/L", font=("Helvetica", 12, "bold")).pack(side=LEFT)
games_label = ttk.Label(games_frame, text="0/0 (0%)")
games_label.pack(side=RIGHT)

top_champs_panel = ttk.Frame(left_block, style="secondary.TFrame")
top_champs_panel.pack(fill=X, padx=5, pady=5)

ttk.Label(top_champs_panel, text="TOP 5 Championów", font=("Helvetica", 14, "bold")).pack(pady=5)

top_champs_container = ttk.Frame(top_champs_panel)
top_champs_container.pack(fill=X, padx=5, pady=5)

# Na początku tworzyłem samemu 5 ramek... XD
for i in range(5):
    champ_frame = ttk.Frame(top_champs_container, style="secondary.TFrame")
    champ_frame.pack(fill=X, pady=2)
    champ_icon_frame = ttk.Frame(champ_frame, width=40, height=40)
    champ_icon_frame.pack(side=LEFT, padx=5, pady=5)
    champ_icon_frame.pack_propagate(False)
    
    champ_icon_label = ttk.Label(champ_icon_frame)
    champ_icon_label.pack(fill=BOTH, expand=True)
    
    champ_info_frame = ttk.Frame(champ_frame)
    champ_info_frame.pack(side=LEFT, fill=X, expand=True, padx=5)
    
    champ_name_label = ttk.Label(champ_info_frame, text="", font=("Helvetica", 10, "bold"))
    champ_name_label.pack(side=LEFT)
    
    champ_stats_label = ttk.Label(champ_info_frame, text="")
    champ_stats_label.pack(side=RIGHT)

match_history_block = ttk.Frame(bottom_section)
match_history_block.pack(side=LEFT, fill=BOTH, expand=True, padx=20)
ttk.Label(match_history_block, text="Historia meczy", font=("Helvetica", 14, "bold")).pack(pady=5)

match_canvas = ttk.Canvas(match_history_block)
match_scrollbar = ttk.Scrollbar(match_history_block, orient="vertical", command=match_canvas.yview)
match_scrollbar.pack(side=RIGHT, fill=Y)

match_canvas.configure(yscrollcommand=match_scrollbar.set)
match_canvas.pack(side=LEFT, fill=BOTH, expand=True)

match_history_panel = ttk.Frame(match_canvas)
match_canvas_window = match_canvas.create_window((0, 0), window=match_history_panel, anchor="nw")

# UGH
def configure_match_scroll(event):
    match_canvas.itemconfig(match_canvas_window, width=match_canvas.winfo_width())
    match_canvas.configure(scrollregion=match_canvas.bbox("all"))

match_history_panel.bind("<Configure>", configure_match_scroll)
match_canvas.bind("<Configure>", lambda e: match_canvas.itemconfig(match_canvas_window, width=match_canvas.winfo_width()))

# To też gotowe zmieniona zmienna
def on_mousewheel(event):
    match_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

match_canvas.bind_all("<MouseWheel>", on_mousewheel)

right_block = ttk.Frame(bottom_section)
right_block.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))

rank_panel = ttk.Frame(right_block, style="secondary.TFrame")
rank_panel.pack(fill=BOTH, expand=True, pady=(0, 10))

rank_icon_frame = ttk.Frame(rank_panel, width=128, height=128)
rank_icon_frame.pack(pady=10)
rank_icon_frame.pack_propagate(False)

rank_icon_label = ttk.Label(rank_icon_frame)
rank_icon_label.pack(fill=BOTH, expand=True)

rank_name = ttk.Label(rank_panel, text="Unranked", font=("Helvetica", 16, "bold"))
rank_name.pack()

winrate_label = ttk.Label(rank_panel, text="Winrate: 0%")
winrate_label.pack()

lp_panel = ttk.Frame(right_block, style="secondary.TFrame")
lp_panel.pack(fill=BOTH, expand=True)

lp_label = ttk.Label(lp_panel, text="LP", font=("Helvetica", 14, "bold"))
lp_label.pack(pady=5)

lp_value = ttk.Label(lp_panel, text="0", font=("Helvetica", 24, "bold"))
lp_value.pack(pady=5)

lastClickX, lastClickY = 0, 0

root.mainloop()

# Nigdy więcej Tkintera!