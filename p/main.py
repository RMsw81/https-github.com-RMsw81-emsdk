import pygame
import random
import time
import datetime
import asyncio
import getpass
#import mimetypes
from flask import Flask, send_from_directory

# Aggiungi il MIME type per i file .wasm
#mimetypes.add_type('application/wasm', '.wasm')

# Configurazione dell'app Flask
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Evita la cache per lo sviluppo

@app.route('/<path:filename>')
def send_file(filename):
    return send_from_directory('p', filename)

# Le variabili globali per facilitare l'esecuzione
COUNT_DOWN = 3

class RecordManager:
    def __init__(self):
        self.records = {}

    def save_record(self, time, user, difficulty):
        best_record = self.load_best_record(user, difficulty)
        if not best_record or time < best_record['time']:
            self.records[(user, difficulty)] = {'time': time, 'date': datetime.datetime.now()}
            print(f"Record salvato per {user} in difficoltà {difficulty}: {time}s")

    def load_best_record(self, user, difficulty):
        return self.records.get((user, difficulty))

def load_image(path):
    try:
        return pygame.image.load(path)
    except pygame.error as e:
        print(f"Impossibile caricare l'immagine da {path}: {e}")
        sys.exit()

class Button:
    def __init__(self, image, position):
        self.image = image
        self.rect = self.image.get_rect(topleft=position)

    def draw(self, screen):
        screen.blit(self.image, self.rect.topleft)

    def click(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class PuzzleGame:
    def __init__(self, image, rows, cols, offset_x=150, offset_y=104):
        self.image = image
        self.rows = rows
        self.cols = cols
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.pieces = []
        self.empty_pos = (cols - 1, rows - 1)
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

class Puzzle:
    def __init__(self, screen, font, clock, user):
        self.screen = screen
        self.font = font
        self.clock = clock
        self.user = user
        self.difficulty = None
        self.game_started = False
        self.alpha = 0
        self.best_time = None
        self.best_time_text = ""
        self.elapsed_time = 0
        self.start_time = None
        self.record_manager = RecordManager()
        self.load_assets()

    def load_assets(self):
        self.background_image = pygame.transform.scale(load_image("assets/games/background.jpg"), (700, 700))
        self.puzzle_images = {
            "easy": pygame.transform.scale(load_image("assets/games/puzzle_image_easy.jpg"), (400, 400)),
            "medium": pygame.transform.scale(load_image("assets/games/puzzle_image_medium.jpg"), (400, 400)),
            "hard": pygame.transform.scale(load_image("assets/games/puzzle_image_hard.jpg"), (400, 400))
        }

        self.start_button = Button(pygame.transform.scale(load_image("assets/games/start_button.png"), (100, 45)), (290, 520))
        self.easy_button = Button(pygame.transform.scale(load_image("assets/games/easy_button.png"), (100, 45)), (180, 550))
        self.medium_button = Button(pygame.transform.scale(load_image("assets/games/medium_button.png"), (100, 45)), (300, 550))
        self.hard_button = Button(pygame.transform.scale(load_image("assets/games/hard_button.png"), (100, 45)), (420, 550))
        self.exit_button = Button(pygame.transform.scale(load_image("assets/games/exit_button.png"), (60, 35)), (510, 570))
        self.back_button = Button(pygame.transform.scale(load_image("assets/games/back_button.png"), (50, 40)), (130, 570))

    def update_best_time_text(self):
        if self.difficulty:
            self.best_time = self.record_manager.load_best_record(self.user, self.difficulty)
            if self.best_time:
                self.best_time_text = f"Tempo: {self.elapsed_time} s Miglior record: {self.best_time['time']} s Utente: {self.user}"
            else:
                self.best_time_text = f"Tempo: {self.elapsed_time} s Nessun record precedente"

    def initialize_puzzle(self, difficulty, rows, cols):
        print(f"Inizializzazione del puzzle con difficoltà: {difficulty}")
        image = self.puzzle_images[difficulty]
        self.puzzle = PuzzleGame(image, rows, cols)
        self.start_time = time.time()  # Inizia il timer
        self.elapsed_time = 0
        self.game_started = True
        self.update_best_time_text()

    def draw(self):
        self.screen.blit(self.background_image, (0, 0))
        if not self.game_started:
            self.start_button.draw(self.screen)
            self.easy_button.draw(self.screen)
            self.medium_button.draw(self.screen)
            self.hard_button.draw(self.screen)
            self.exit_button.draw(self.screen)
        else:
            self.puzzle.draw(self.screen)
            self.update_elapsed_time()
            self.draw_texts()

    def draw_texts(self):
        elapsed_time_text = self.font.render(f"Tempo: {self.elapsed_time:.2f}s", True, (255, 255, 255))
        self.screen.blit(elapsed_time_text, (10, 10))
        if self.best_time_text:
            best_time_text_rendered = self.font.render(self.best_time_text, True, (255, 255, 255))
            self.screen.blit(best_time_text_rendered, (10, 40))

    def update_elapsed_time(self):
        if self.game_started and self.start_time:
            self.elapsed_time = time.time() - self.start_time

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.game_started:
                if self.start_button.click(event):
                    print("Pulsante Start cliccato")
                    self.initialize_puzzle("easy", 3, 3)
            else:
                self.puzzle.handle_click(event.pos)
                if self.puzzle.check_win():
                    print("Puzzle completato!")
                    self.record_manager.save_record(self.elapsed_time, self.user, self.difficulty)
                    self.game_started = False

async def main():
    pygame.init()
    screen = pygame.display.set_mode((700, 700))
    font = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()

    user = getpass.getuser()

    puzzle_game = Puzzle(screen, font, clock, user)

    # Ciclo principale del gioco
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            puzzle_game.handle_event(event)

        puzzle_game.draw()

        pygame.display.flip()
        await asyncio.sleep(0)  # Rende il ciclo compatibile con l'asincronia

    pygame.quit()

if __name__ == "__main__":
    # Avvia il server Flask in un thread separato
    from threading import Thread

    def run_flask():
        app.run(port=5000)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    asyncio.run(main())
