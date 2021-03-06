import click
import random

from tqdm import tqdm
from collections import Counter
from joblib import Parallel, delayed
from typing import List, Set
from dataclasses import dataclass, field


# Get the master list of words
with open("words.txt", mode='r') as f:
    words = f.readlines()
words = [word.strip() for word in words]


@dataclass
class GameState:
    """
    A mutable object that represents the current state of the game.
    """
    found_letters: List[str] = field(default_factory=lambda: [None] * 5)
    loose_letters: List[str] = field(default_factory=list)
    invalid_letters: Set[str] = field(default_factory=set)
    guesses: List[str] = field(default_factory=list)
    valid_guesses: List[str] = field(default_factory=words.copy)

    @property
    def turns(self):
        return len(self.guesses)

    def clone(self):
        return GameState(
            found_letters=self.found_letters.copy(),
            loose_letters=self.loose_letters.copy(),
            invalid_letters=self.invalid_letters.copy(),
            guesses=self.guesses.copy())

    def check_word(self, word):
        # Does the word contain invalid letters?
        for l in word:
            if l in self.invalid_letters:
                return False

        # Create a pool of remaining letters to match against
        guess_letters = [l for l in word]

        # Scan through the found letters
        for wl, fl in zip(word, self.found_letters):
            if fl != None:
                if wl != fl:
                    # Found letter is in the incorrect spot
                    return False
                # This letter has been found, remove it from the pool
                guess_letters.remove(fl)

        # Are ALL loose letters contained within the remaining letters?
        for l in self.loose_letters:
            if l in guess_letters:
                # If there are two of the same letter, there need to be two in the word as well
                guess_letters.remove(l)
            else:
                return False

        # Are there any letters that are being tried again in the same spot?
        for guess in self.guesses:
            for wl, gl, fl in zip(word, guess, self.found_letters):
                if not fl and wl == gl:
                    return False

        return True

    def add_guess(self, guess_word, goal_word):
        self.guesses.append(guess_word)

        # Find exact matches
        for i, (guess_letter, goal_letter) in enumerate(zip(guess_word, goal_word)):
            if guess_letter == goal_letter:
                self.found_letters[i] = guess_letter
                if guess_letter in self.loose_letters:
                    self.loose_letters.remove(guess_letter)

        # Create a pool of remaining letters to match against
        goal_letters = [l for l in goal_word]
        guess_letters = [l for l in guess_word]
        for i, found_letter in enumerate(self.found_letters):
            if found_letter != None:
                goal_letters.remove(found_letter)
                if guess_word[i] == found_letter:
                    guess_letters.remove(found_letter)

        # Remove the existing letters from the loose pool to avoid repeats
        for l in guess_letters:
            if l in self.loose_letters:
                self.loose_letters.remove(l)

        # Search for loose letters, move them from the goal word into
        # the loose letter pool
        for l in guess_letters:
            if l in goal_letters:
                self.loose_letters.append(l)
                goal_letters.remove(l)

        # Add uniquely invalid letters to the invalid pool
        for l in guess_word:
            if l not in goal_word:
                self.invalid_letters.add(l)

        self.valid_guesses = [
            word for word in self.valid_guesses if self.check_word(word)]


MAX_TURNS = 16


def play_game(goal_word, input_source, display=lambda _="": ()):
    # Simulates a game played with a given strategy
    turn = 0
    game_state = GameState()
    while turn < MAX_TURNS:
        turn += 1

        # Print the current state
        display("".join(l if l else "-" for l in game_state.found_letters))
        display(f"Loose letters: {game_state.loose_letters}")
        display(f"Invalid letters: {game_state.invalid_letters}")

        # Make a guess
        guess_word = input_source(game_state)
        display(f"Guessed {guess_word}")
        if guess_word == goal_word:
            display(f"The word was {goal_word}!")
            return turn
        display()

        # Add guess to game state
        game_state.add_guess(guess_word, goal_word)

    return turn


def get_letter_scores(words):
    all_letters = (letter for word in words for letter in word)
    return Counter(all_letters)


def get_word_score(word, letter_score):
    return sum(letter_score[letter] for letter in set(word))


global_letter_score = get_letter_scores(words)
global_word_score = {word: get_word_score(
    word, global_letter_score) for word in words}
sorted_words = sorted(
    global_word_score, key=global_word_score.get, reverse=True)


def pick_best_word_v1(game_state: GameState):
    """
    Pick the best word based on global letter scores.  
    Picks the highest scoring word that is still possible and hasn't already been guessed
    Only provides valid guesses
    """
    return next(word for word in sorted_words if game_state.check_word(word))


def pick_best_word_v2(game_state):
    """
    Same as V1 but recalculates letter scores based on the remaining words
    1. Get all the remaining valid words
    2. Recalculate letter scores for the remaining letters
    Only provides valid guesses
    """
    letter_score = get_letter_scores(game_state.valid_guesses)
    return max(game_state.valid_guesses, key=lambda word: get_word_score(word, letter_score))


def pick_best_word_v3(game_state: GameState):
    """
    Same as V2 but will consider all words. 
    When there is only one valid word left, it will guess it.
    """
    if len(game_state.valid_guesses) == 1:
        return game_state.valid_guesses[0]
    letter_score = get_letter_scores(game_state.valid_guesses)
    return max(words, key=lambda word: get_word_score(word, letter_score))


def pick_best_word_v4(game_state: GameState):
    """
    Uses v3 for the first few guesses, then uses v2
    """
    turn = len(game_state.guesses)
    if turn < 4:
        return pick_best_word_v3(game_state)
    else:
        return pick_best_word_v2(game_state)


def pick_best_word_v5(game_state: GameState):
    def eval_word(word):
        score = 0
        for valid_word in game_state.valid_guesses:
            new_state = game_state.clone()
            new_state.add_guess(word, valid_word)
            score += len(new_state.valid_guesses)
        score = score / len(game_state.valid_guesses)
        return score

    word_scores = Parallel(n_jobs=16)(
        delayed(eval_word)(word=word) for word in tqdm(words))
    return min(word_scores)


def evaluate_strategy(strategy, words=words):
    word_difficulty = Parallel(n_jobs=16)(delayed(play_game)(
        goal_word=word, input_source=strategy) for word in tqdm(words))
    difficulty_spread = Counter(word_difficulty)
    average_turns = sum(word_difficulty) / len(words)
    num_solved = len(
        [turn_count for turn_count in word_difficulty if turn_count <= 6])
    print(f"{difficulty_spread=}")
    print(f"{average_turns=:.2f}")
    print(f"{num_solved=} ({num_solved / len(words) * 100:.1f}%)")
    return average_turns


def find_problematic_word(strategy):
    for word in words:
        turns = play_game(word, strategy)
        if turns > 10:
            return word


def parse_strategy(strategy):
    if strategy.upper() == "V1":
        return pick_best_word_v1
    if strategy.upper() == "V2":
        return pick_best_word_v2
    if strategy.upper() == "V3":
        return pick_best_word_v3
    if strategy.upper() == "V4":
        return pick_best_word_v4
    if strategy.upper() == "V5":
        return pick_best_word_v5


@click.command()
@click.option("--strategy", default="v2",
              type=click.Choice(["v1", "v2", "v3", "v4", "v5"],
                                case_sensitive=False),
              help="Pick which strategy to evaluate")
@click.option("--word", default=None, help="Optionally evaluate a single word")
def evaluate(strategy, word):
    strategy_func = parse_strategy(strategy)
    if word:
        play_game(word, strategy_func, print)
    else:
        evaluate_strategy(strategy_func)


@click.command()
@click.option("--hardmode", flag_value=True, help="Play on hard mode")
@click.option("--word", default=None, help="Play against a specific word")
def play(hardmode, word):
    def make_guess(game_state):
        guess = ""
        while True:
            guess = input("Guess a word: ")
            if guess not in words:
                print("Guess must be a valid word, try again.")
                continue
            if hardmode and not game_state.check_word(guess):
                print("In hard mode every guess must be a valid answer, try again.")
                continue
            break
        return guess
    if not word:
        word = random.choice(words)
    play_game(word, make_guess, print)


@click.command()
@click.option("--strategy", default="v2",
              type=click.Choice(["v1", "v2", "v3", "v4", "v5"],
                                case_sensitive=False),
              help="Pick which strategy to use")
def cheat(strategy):
    strategy_func = parse_strategy(strategy)
    game_state = GameState()
    while True:
        # Generate a guess
        guess = strategy_func(game_state)
        print(f"Try word: {guess}")

        # Ask for some input about the game state
        found_letters = input(
            "Please input the word so far using \"-\" in place of missing letters: ")
        loose_letters = input(
            "Please enter ALL loose letters separated by spaces: ")

        # Add the guess to the game state
        game_state.guesses.append(guess)

        # If split returns an empty string, remove it from the loose letters
        for i, l in enumerate(found_letters):
            if l != "-":
                game_state.found_letters[i] = l

        # Hooray if we got it!
        if all(game_state.found_letters):
            print("We did it!")
            return

        # Add loose letters to the game state
        game_state.loose_letters = list(loose_letters)

        # Add invalid letters to the game state
        for word in game_state.guesses:
            for l in word:
                if l not in game_state.found_letters and l not in game_state.loose_letters:
                    game_state.invalid_letters.add(l)

        print(game_state)


@click.group()
def cli():
    pass


if __name__ == "__main__":
    cli.add_command(evaluate)
    cli.add_command(play)
    cli.add_command(cheat)
    cli()
