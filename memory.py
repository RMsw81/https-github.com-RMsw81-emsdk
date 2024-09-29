import datetime
import pygame
import sys
import random
import pymysql
import os
from button import Button

# Costanti per le dimensioni e le risorse
CARD_SIZE = (190, 220)  # Dimensioni delle carte
CARD_SPACING = -75  # Spaziatura tra le carte
COVER_IMAGE = 'assets/games/casellar.png'  # Immagine di copertura delle carte
CLICK_SOUND = 'assets/games/click_sound.wav'  # Suono per il clic
WIN_SOUND = 'assets/games/win_sound.wav'  # Suono per la vittoria
WINDOW_SIZE = (1200, 800)  # Dimensioni della finestra di gioco
VICTORY_IMAGE = 'assets/games/victory.png'  # Immagine da mostrare alla vittoria
VICTORY_IMAGE_SIZE = (500, 400)  # Dimensioni dell'immagine di vittoria
BACKGROUND_IMAGE = 'assets/games/background.png'  # Immagine di sfondo

# Mappa delle difficoltà
DIFFICULTY_MAP = {
    'easy': 8,
    'medium': 12,
    'hard': 16
}

# Classe per gestire la connessione al database
class Database:
    def __init__(self):
        try:
            # Leggi le variabili d'ambiente
            db_host = 'RobertaMerlo.mysql.pythonanywhere-services.com'
            db_user = 'RobertaMerlo'
            db_password = 'Y9puX%40a8'  
                db_name = 'RobertaMerlo$db'
            # Crea la connessione
            self.conn = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                port=db_port
            )
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
            self.create_table()  # Creazione della tabella se non esiste
        except pymysql.MySQLError as e:
            print(f"Errore nella connessione al database: {e}")
            sys.exit()

    def create_table(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    time FLOAT,
                    date DATETIME,
                    user VARCHAR(255),
                    difficulty VARCHAR(255)
                )
            ''')
            self.conn.commit()
        except pymysql.MySQLError as e:
            print(f"Errore nella creazione della tabella: {e}")
            sys.exit()

    def save_record(self, new_time, user, difficulty):
        # Salva il record solo se il nuovo tempo è migliore
        best_record = self.load_best_record(user, difficulty)
        if not best_record or new_time < best_record['time']:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO records (time, date, user, difficulty) VALUES (%s, %s, %s, %s)",
                (new_time, current_time, user, difficulty)
            )
            self.conn.commit()

    def load_best_record(self, user, difficulty):
        self.cursor.execute(
            "SELECT time, date, user, difficulty FROM records WHERE user = %s AND difficulty = %s ORDER BY time ASC LIMIT 1",
            (user, difficulty)
        )
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()

    # Funzione per aggiornare il miglior tempo e record dinamicamente
    def update_best_time_text(db, user, difficulty, elapsed_time):
        user = user
        best_time = None
        best_record = db.load_best_record(user, difficulty)
        if best_record:
            best_time = best_record['time']
            best_time_text = f"Tempo: {elapsed_time} s - Miglior record: {best_record['time']} s - Utente: {best_record['user']}"
        else:
            best_time_text = f"Tempo: {elapsed_time} s - Nessun record precedente"
    
        return best_time, best_time_text

# Funzione per caricare le immagini
def load_image(path):
    try:
        image = pygame.image.load(path)
        return image
    except pygame.error as e:
        print(f"Impossibile caricare l'immagine da {path}: {e}")
        sys.exit()

# Funzione per caricare i suoni
def load_sounds():
    try:
        click_sound = pygame.mixer.Sound(CLICK_SOUND)
    except pygame.error as e:
        print(f"Errore nel caricamento del suono 'click_sound.wav': {e}")
        click_sound = None

    try:
        win_sound = pygame.mixer.Sound(WIN_SOUND)
    except pygame.error as e:
        print(f"Errore nel caricamento del suono 'win_sound.wav': {e}")
        win_sound = None

    return click_sound, win_sound

# Funzione per caricare le immagini necessarie
def load_images():
    images = []
    for i in range(16):
        try:
            img = pygame.image.load(f'assets/games/casella{i+1}.png').convert_alpha()
            img = pygame.transform.scale(img, CARD_SIZE)
            images.append(img)
        except pygame.error as e:
            print(f"Errore nel caricamento dell'immagine 'assets/games/casella{i+1}.png': {e}")
            images.append(None)
    
    try:
        cover_image = pygame.image.load(COVER_IMAGE).convert_alpha()
        cover_image = pygame.transform.scale(cover_image, CARD_SIZE)
    except pygame.error as e:
        print(f"Errore nel caricamento dell'immagine cover '{COVER_IMAGE}': {e}")
        cover_image = None
    
    try:
        victory_image = pygame.image.load(VICTORY_IMAGE).convert_alpha()
        victory_image = pygame.transform.scale(victory_image, VICTORY_IMAGE_SIZE)
    except pygame.error as e:
        print(f"Errore nel caricamento dell'immagine di vittoria '{VICTORY_IMAGE}': {e}")
        victory_image = None

    try:
        background_image = pygame.image.load(BACKGROUND_IMAGE).convert()
        background_image = pygame.transform.scale(background_image, WINDOW_SIZE)
    except pygame.error as e:
        print(f"Errore nel caricamento dell'immagine di sfondo '{BACKGROUND_IMAGE}': {e}")
        background_image = None

    return images, cover_image, victory_image, background_image

# Funzione per creare la griglia di gioco basata sulla difficoltà scelta
def create_grid(difficulty, images):
    if difficulty not in DIFFICULTY_MAP:
        raise ValueError("Difficoltà non valida. Deve essere 'easy', 'medium' o 'hard'.")

    num_pairs = DIFFICULTY_MAP[difficulty]
    if num_pairs > len(images):
        raise ValueError("Non ci sono abbastanza immagini per il livello scelto.")
    
    selected_images = random.sample([img for img in images if img is not None], num_pairs)
    card_list = selected_images * 2  
    random.shuffle(card_list)

    num_cards = num_pairs * 2
    num_rows = 4
    num_cols = (num_cards + num_rows - 1) // num_rows

    grid = [[None] * num_cols for _ in range(num_rows)]

    index = 0
    for r in range(num_rows):
        for c in range(num_cols):
            if index < len(card_list):
                grid[r][c] = card_list[index]
                index += 1

    return grid, num_cols

# Classe per gestire una carta nel gioco
class Card:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect
        self.covered = True

    def draw(self, screen, cover_image):
        if self.covered:
            screen.blit(cover_image, self.rect.topleft)
        else:
            screen.blit(self.image, self.rect.topleft)

    def flip(self):
        self.covered = not self.covered

# Funzione per disegnare il testo sullo schermo
def draw_text(screen, text, position, font, color=(255, 255, 255)):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, position)

# Funzione principale per iniziare il gioco di memoria
def start_memory_game(user, difficulty):
    db = Database()  # Connessione al database
    
    # Caricamento del miglior record per l'utente e la difficoltà scelta
    best_record = db.load_best_record(user, difficulty)
    best_time = best_record['time'] if best_record else None
    #user = best_record['user'] if best_record else None

    # Inizializzazione di Pygame e creazione della finestra di gioco
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption('Memory Game')

    # Caricamento delle immagini e dei suoni
    images, cover_image, victory_image, background_image = load_images()
    click_sound, win_sound = load_sounds()

    # Creazione della griglia di gioco
    grid, num_cols = create_grid(difficulty, images)
    cards = []
    card_width, card_height = CARD_SIZE
    spacing = CARD_SPACING

    # Calcolo delle posizioni iniziali per le carte
    start_x = (WINDOW_SIZE[0] - (card_width + spacing) * num_cols + spacing) // 2
    start_y = (WINDOW_SIZE[1] - (card_height + spacing) * 4 + spacing) // 2

    # Creazione degli oggetti carta e loro posizionamento
    for r in range(4):
        for c in range(num_cols):
            image = grid[r][c]
            if image is not None:
                rect = pygame.Rect(
                    start_x + c * (card_width + spacing),
                    start_y + r * (card_height + spacing),
                    card_width,
                    card_height
                )
                cards.append(Card(image, rect))

    first_card = None
    second_card = None
    matches = 0
    num_pairs = DIFFICULTY_MAP[difficulty]
    start_time = pygame.time.get_ticks()  # Tempo di inizio gioco
    game_over = False
    score = 0
    consecutive_matches = 0
    reveal_delay = 1000  # Ritardo per mostrare le carte

    font = pygame.font.Font(None, 36)
    showing_cards = False
    show_start_time = 0

    # Creazione dei pulsanti
    button_width, button_height = 110, 60
    back_button = Button(pygame.transform.scale(load_image('assets/games/back_button.png'), (button_width, button_height)), (15, 250))
    start_button = Button(pygame.transform.scale(load_image('assets/games/start_button.png'), (button_width, button_height)), (15, 350))
    exit_button = Button(pygame.transform.scale(load_image('assets/games/exit_button.png'), (button_width, button_height)), (15, 450))

    clock = pygame.time.Clock()
    while not game_over:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                db.close()
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if back_button.click(event):
                    db.close()
                    return 'selection'
                if start_button.click(event):
                    return 'game'
                if exit_button.click(event):
                    db.close()
                    pygame.quit()
                    sys.exit()

                for card in cards:
                    if card.rect.collidepoint(pos) and card.covered and not showing_cards:
                        if click_sound:
                            click_sound.play()
                        card.flip()

                        if first_card is None:
                            first_card = card
                        elif second_card is None:
                            second_card = card
                            show_start_time = pygame.time.get_ticks()
                            showing_cards = True

        if showing_cards and pygame.time.get_ticks() - show_start_time > reveal_delay:
            if first_card.image == second_card.image:
                cards = [card for card in cards if card != first_card and card != second_card]
                matches += 1
                consecutive_matches += 1
                points = 20 * consecutive_matches
                score += points
                if matches == num_pairs:
                    game_over = True
                    end_time = pygame.time.get_ticks()
                    if win_sound:
                        win_sound.play()
                    elapsed_time = (end_time - start_time) // 1000
                    if best_time is None or elapsed_time < best_time:
                        db.save_record(elapsed_time, user, difficulty)
            else:
                first_card.flip()
                second_card.flip()
                consecutive_matches = 0

            first_card = None
            second_card = None
            showing_cards = False

        screen.blit(background_image, (0, 0))  # Disegnare l'immagine di sfondo
        for card in cards:
            card.draw(screen, cover_image)
        
        elapsed_time = (pygame.time.get_ticks() - start_time) // 1000
        draw_text(screen, f"Tempo: {elapsed_time} s - Miglior record: {best_time} s Utente: {user}", (10, 10), font)
        draw_text(screen, f"Punteggio: {score}", (10, 50), font)

        if best_time is None:
            draw_text(screen, f"Nessun Record.", (10, 90), font)
        
        # Disegnare i pulsanti
        back_button.draw(screen)
        start_button.draw(screen)
        exit_button.draw(screen)
        
        pygame.display.flip()
        clock.tick(60)

    # Mostrare l'immagine di vittoria
    while game_over:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_button.click(event):
                    db.close()
                    return 'selection'
                if start_button.click(event):
                    start_memory_game(user, difficulty)
                    return 'game'
                if exit_button.click(event):
                    db.close()
                    pygame.quit()
                    sys.exit()

        screen.blit(background_image, (0, 0))  # Disegnare l'immagine di sfondo
        screen.blit(victory_image, ((WINDOW_SIZE[0] - VICTORY_IMAGE_SIZE[0]) // 2, (WINDOW_SIZE[1] - VICTORY_IMAGE_SIZE[1]) // 2))
        draw_text(screen, f"Tempo: {elapsed_time} s - Miglior record: {best_time} s Utente: {user}", (10, 10), font)
        
        # Disegnare i pulsanti
        back_button.draw(screen)
        start_button.draw(screen)
        exit_button.draw(screen)
        
        pygame.display.flip()
        clock.tick(60)

# Funzione per iniziare il menu di selezione
def start_memory(user):
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption('Memory Game - Seleziona la Difficoltà')

    # Dimensioni dei pulsanti
    button_width, button_height = 120, 60
    spacing = 100  # Spazio tra i pulsanti

    # Caricamento delle immagini dei pulsanti
    easy_image = pygame.transform.scale(load_image('assets/games/easy_button.png'), (button_width, button_height))
    medium_image = pygame.transform.scale(load_image('assets/games/medium_button.png'), (button_width, button_height))
    hard_image = pygame.transform.scale(load_image('assets/games/hard_button.png'), (button_width, button_height))
    start_image = pygame.transform.scale(load_image('assets/games/start_button.png'), (button_width, button_height))
    back_image = pygame.transform.scale(load_image('assets/games/back_button.png'), (90, 55))
    exit_image = pygame.transform.scale(load_image('assets/games/exit_button.png'), (button_width, button_height))

    # Creazione dei pulsanti
    easy_button = Button(easy_image, (0, 0))
    medium_button = Button(medium_image, (0, 0))
    hard_button = Button(hard_image, (0, 0))
    start_button = Button(start_image, (0, 0))
    back_button = Button(back_image, (0, 0))
    exit_button = Button(exit_image, (0, 0))

    selected_difficulty = None
    game_state = 'selection'

    background_image = load_image(BACKGROUND_IMAGE)
    background_image = pygame.transform.scale(background_image, WINDOW_SIZE)

    # Calcolo delle posizioni orizzontali dei pulsanti
    num_buttons = 3  # Numero di pulsanti
    total_buttons_width = button_width * num_buttons + spacing * (num_buttons - 1)
    start_x = (WINDOW_SIZE[0] - total_buttons_width) // 2  # X iniziale per centrare i pulsanti

    easy_button.rect.topleft = (start_x, 300)
    medium_button.rect.topleft = (start_x + button_width + spacing, 300)
    hard_button.rect.topleft = (start_x + 2 * (button_width + spacing), 300)
    start_button.rect.topleft = (start_x + button_width + spacing, 300)
    back_button.rect.topleft = (start_x, 300)
    exit_button.rect.topleft = (start_x + 2 * (button_width + spacing), 300)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == 'selection':
                    if easy_button.click(event):
                        selected_difficulty = 'easy'
                        game_state = 'game_options'
                    elif medium_button.click(event):
                        selected_difficulty = 'medium'
                        game_state = 'game_options'
                    elif hard_button.click(event):
                        selected_difficulty = 'hard'
                        game_state = 'game_options'

                elif game_state == 'game_options':
                    if start_button.click(event) and selected_difficulty is not None:
                        # Passaggio esplicito del nome utente
                        if start_memory_game(user, selected_difficulty) == 'selection':
                            game_state = 'selection'
                    if back_button.click(event):
                        selected_difficulty = None
                        game_state = 'selection'
                    if exit_button.click(event):
                        pygame.quit()
                        sys.exit()

        screen.blit(background_image, (0, 0))  # Disegnare l'immagine di sfondo

        if game_state == 'selection':
            easy_button.draw(screen)
            medium_button.draw(screen)
            hard_button.draw(screen)
        elif game_state == 'game_options':
            start_button.draw(screen)
            back_button.draw(screen)
            exit_button.draw(screen)

        pygame.display.flip()

# Funzione principale per l'esecuzione dello script
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python memory.py <username>")
        sys.exit(1)

    user = sys.argv[1]
   # print(f"Username provided: {user}")
    start_memory(user)
