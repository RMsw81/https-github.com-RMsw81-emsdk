import pygame
import random
import time
import datetime
import sys
import pymysql
from button import Button  

# Classe per gestire la connessione al database
class Database:
    def __init__(self):
        self.conn = pymysql.connect(
            host="localhost",
            user="user",
            password="Y9puX%40a8",
            database="db",
            cursorclass=pymysql.cursors.DictCursor
        )
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
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

# Funzione per caricare un'immagine
def load_image(path):
    try:
        return pygame.image.load(path)
    except pygame.error as e:
        print(f"Impossibile caricare l'immagine da {path}: {e}")
        sys.exit()

# Classe per gestire il gioco del puzzle
class PuzzleGame:
    def __init__(self, image, rows, cols, offset_x=150, offset_y=104, click_sound=None, win_sound=None):
        self.image = image
        self.rows = rows
        self.cols = cols
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.pieces = []
        self.empty_pos = (cols - 1, rows - 1)
        self.click_sound = click_sound
        self.win_sound = win_sound
        self.create_pieces()
        self.shuffle_pieces()

    def create_pieces(self):
        piece_width = self.image.get_width() // self.cols
        piece_height = self.image.get_height() // self.rows
        for row in range(self.rows):
            for col in range(self.cols):
                if (row, col) != self.empty_pos:
                    rect = pygame.Rect(col * piece_width, row * piece_height, piece_width, piece_height)
                    piece_image = self.image.subsurface(rect)
                    self.pieces.append({
                        'image': piece_image,
                        'current_pos': (col, row),
                        'correct_pos': (col, row)
                    })

    def shuffle_pieces(self, max_attempts=1000):
        attempts = 0
        while attempts < max_attempts:
            piece_positions = [piece['current_pos'] for piece in self.pieces]
            random.shuffle(piece_positions)
            for i, piece in enumerate(self.pieces):
                piece['current_pos'] = piece_positions[i]

            if self.is_solvable():
                break

            attempts += 1
        else:
            raise RuntimeError("Impossibile generare un puzzle risolvibile dopo molti tentativi.")

    def draw(self, screen):
        piece_width = self.image.get_width() // self.cols
        piece_height = self.image.get_height() // self.rows
        for piece in self.pieces:
            x, y = piece['current_pos']
            screen.blit(piece['image'], (self.offset_x + x * piece_width, self.offset_y + y * piece_height))

    def handle_click(self, position):
        piece_width = self.image.get_width() // self.cols
        piece_height = self.image.get_height() // self.rows
        x = (position[0] - self.offset_x) // piece_width
        y = (position[1] - self.offset_y) // piece_height

        if x < 0 or x >= self.cols or y < 0 or y >= self.rows:
            return

        if (x, y) == self.empty_pos:
            return

        if self.is_adjacent((x, y), self.empty_pos):
            for piece in self.pieces:
                if piece['current_pos'] == (x, y):
                    piece['current_pos'], self.empty_pos = self.empty_pos, piece['current_pos']
                    if self.click_sound:
                        self.click_sound.play()
                    if self.check_win():
                        if self.win_sound:
                            self.win_sound.play()
                    break

    def is_adjacent(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]) == 1

    def check_win(self):
        return all(piece['current_pos'] == piece['correct_pos'] for piece in self.pieces)

    def is_solvable(self):
        inversions = 0
        one_d_pieces = []

        for row in range(self.rows):
            for col in range(self.cols):
                if (col, row) != self.empty_pos:
                    one_d_pieces.append(
                        self.pieces[row * self.cols + col]['current_pos'][1] * self.cols +
                        self.pieces[row * self.cols + col]['current_pos'][0]
                    )

        for i in range(len(one_d_pieces)):
            for j in range(i + 1, len(one_d_pieces)):
                if one_d_pieces[i] > one_d_pieces[j]:
                    inversions += 1

        if self.cols % 2 == 1:
            return inversions % 2 == 0
        else:
            empty_row_from_bottom = self.rows - self.empty_pos[1]
            return (inversions + empty_row_from_bottom) % 2 == 1

# Classe principale per gestire la logica del puzzle e l'interfaccia utente
class Puzzle:
    def __init__(self, screen, font, clock, user):
        self.screen = screen
        self.font = font
        self.clock = clock
        self.user = user
        self.difficulty = None
        self.game_started = False
        self.win_animation = False
        self.alpha = 0
        self.best_time = None
        self.best_time_text = ""
        self.elapsed_time = 0
        self.start_time = None
        self.db = Database()
        self.load_assets()

    def load_assets(self):
        self.background_image = pygame.transform.scale(load_image("assets/games/background.jpg"), (700, 700))
        self.puzzle_images = {
            "easy": pygame.transform.scale(load_image("assets/games/puzzle_image_easy.jpg"), (400, 400)),
            "medium": pygame.transform.scale(load_image("assets/games/puzzle_image_medium.jpg"), (400, 400)),
            "hard": pygame.transform.scale(load_image("assets/games/puzzle_image_hard.jpg"), (400, 400))
        }
        self.click_sound = pygame.mixer.Sound("assets/games/click_sound.wav")
        self.win_sounds = {
            "easy": pygame.mixer.Sound("assets/games/win_sound_easy.wav"),
            "medium": pygame.mixer.Sound("assets/games/win_sound_medium.wav"),
            "hard": pygame.mixer.Sound("assets/games/win_sound_hard.wav")
        }

        # Pulsanti del menu
        self.start_button = Button(pygame.transform.scale(load_image("assets/games/start_button.png"), (100, 45)), (290, 520))
        self.easy_button = Button(pygame.transform.scale(load_image("assets/games/easy_button.png"), (100, 45)), (180, 550))
        self.medium_button = Button(pygame.transform.scale(load_image("assets/games/medium_button.png"), (100, 45)), (300, 550))
        self.hard_button = Button(pygame.transform.scale(load_image("assets/games/hard_button.png"), (100, 45)), (420, 550))
        self.exit_button = Button(pygame.transform.scale(load_image("assets/games/exit_button.png"), (60, 35)), (510, 570))
        self.back_button = Button(pygame.transform.scale(load_image("assets/games/back_button.png"), (50, 40)), (130, 570))

    def update_best_time_text(self):
        if self.difficulty:
            self.best_time = self.db.load_best_record(self.user, self.difficulty)
            if self.best_time:
                self.best_time_text = f"Tempo: {self.elapsed_time} s Miglior record: {self.best_time['time']} s Utente: {self.best_time['user']}"
            else:
                self.best_time_text = f"Tempo: {self.elapsed_time} s Nessun record precedente"

    def initialize_puzzle(self, difficulty, rows, cols):
        print(f"Inizializzazione del puzzle con difficoltà: {difficulty}")
        image = self.puzzle_images[difficulty]
        self.puzzle = PuzzleGame(image, rows, cols, click_sound=self.click_sound, win_sound=self.win_sounds[difficulty])
        self.start_time = time.time()  # Registra il tempo di inizio del gioco
        self.elapsed_time = 0  # Tempo trascorso
        self.update_best_time_text()  # Aggiorna il miglior record per la nuova difficoltà

        # Reset delle variabili relative all'animazione di vittoria
        self.win_animation = False
        self.alpha = 0

    def draw_game_screen(self):
        # Disegna lo schermo del gioco
        self.screen.blit(self.background_image, (0, 0))  # Disegna lo sfondo
        
        if self.best_time_text:
            record_text = self.font.render(self.best_time_text, True, (255, 255, 255))
            self.screen.blit(record_text, (10, 20))  # Mostra il miglior record

        if self.game_started:
            self.puzzle.draw(self.screen)  # Disegna il puzzle se il gioco è iniziato

            if self.win_animation:
                fade_surface = self.puzzle_images[self.difficulty].copy()
                fade_surface.set_alpha(self.alpha)
                self.screen.blit(fade_surface, (150, 104))  # Mostra l'immagine di vittoria

                self.alpha += 5
                if self.alpha > 255:
                    self.alpha = 255

            if self.puzzle.check_win():
                if not self.win_animation:
                    print("Puzzle completato!")
                    self.win_sounds[self.difficulty].play()
                    self.win_animation = True
                    self.game_started = False
                    self.db.save_record(self.elapsed_time, self.user, self.difficulty)
                    self.update_best_time_text()  # Aggiorna il miglior record al termine del gioco

            # Mostra i pulsanti "Start", "Back" ed "Exit" quando il gioco è finito
            self.start_button.draw(self.screen)
            self.exit_button.draw(self.screen)
            self.back_button.draw(self.screen)

        else:
            if self.difficulty:
                # Mostra l'immagine del puzzle solo se non è stato avviato il gioco
                self.screen.blit(self.puzzle_images[self.difficulty], (150, 104))
                self.start_button.draw(self.screen)
                self.exit_button.draw(self.screen)
                self.back_button.draw(self.screen)

            # Mostra i pulsanti di selezione della difficoltà solo se non è stato selezionato alcun livello
            if not self.difficulty:
                self.easy_button.draw(self.screen)
                self.medium_button.draw(self.screen)
                self.hard_button.draw(self.screen)

        pygame.display.flip()  # Aggiorna il display

    def run(self):
        # Ciclo principale del gioco
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    print(f"Click del mouse alla posizione {event.pos}")
                    if self.start_button.click(event):
                        if self.difficulty:
                            rows, cols = (3, 3) if self.difficulty == "easy" else (4, 4) if self.difficulty == "medium" else (5, 5)
                            self.initialize_puzzle(self.difficulty, rows, cols)
                            self.game_started = True
                        else:
                            print("Seleziona un livello di difficoltà.")
                    elif self.easy_button.click(event):
                        self.difficulty = "easy"
                        print("Difficoltà impostata su easy")
                        self.update_best_time_text()
                    elif self.medium_button.click(event):
                        self.difficulty = "medium"
                        print("Difficoltà impostata su medium")
                        self.update_best_time_text()
                    elif self.hard_button.click(event):
                        self.difficulty = "hard"
                        print("Difficoltà impostata su hard")
                        self.update_best_time_text()
                    elif self.exit_button.click(event):
                        print("Pulsante Exit cliccato")
                        running = False
                    elif self.back_button.click(event):
                        self.difficulty = None
                        self.game_started = False
                        print("Tornato alla selezione della difficoltà")

                    if self.game_started:
                        self.puzzle.handle_click(event.pos)

            if self.game_started:
                self.elapsed_time = int(time.time() - self.start_time)  # Aggiorna il tempo trascorso
                self.update_best_time_text()  # Aggiorna il testo del miglior tempo
            self.draw_game_screen()

            self.clock.tick(60)  # Limita il frame rate a 60 FPS
        pygame.quit()  # Chiude Pygame
        self.db.close()  # Chiude la connessione al database

# Funzione principale per avviare il gioco
def start_game(user):
    pygame.init()  # Inizializza Pygame
    screen_width, screen_height = 700, 700
    screen = pygame.display.set_mode((screen_width, screen_height))  # Imposta le dimensioni della finestra
    pygame.display.set_caption("Puzzle Game")  # Imposta il titolo della finestra

    font = pygame.font.Font(None, 24)  # Crea un oggetto Font
    clock = pygame.time.Clock()  # Crea un oggetto Clock

    game = Puzzle(screen, font, clock, user)  # Crea un'istanza della classe Puzzle
    game.run()  # Avvia il ciclo principale del gioco

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python puzzle.py <username>")
        sys.exit(1)

    user = sys.argv[1]
    start_game(user)  # Avvia il gioco con il nome utente specificato
