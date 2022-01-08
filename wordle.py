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

    @property
    def turns(self):
        return len(self.guesses)


def play_game(goal_word, input_source=input, display=lambda _="": ()):
    # Simulates a game played with a given strategy
    turn = 0
    game_state = GameState()
    while turn < 1000:
        turn += 1

        # Print the current state
        display("".join(l if l else "-" for l in game_state.found_letters))
        display(f"Loose letters: {game_state.loose_letters}")
        display(f"Invalid letters: {game_state.invalid_letters}")

        # Make a guess
        guess_word = input_source(game_state)
        game_state.guesses.append(guess_word)
        display(f"Guessed {guess_word}")
        if guess_word == goal_word:
            display(f"The word was {goal_word}!")
            return turn
        display()

        # Find exact matches
        for i, (guess_letter, goal_letter) in enumerate(zip(guess_word, goal_word)):
            if guess_letter == goal_letter:
                game_state.found_letters[i] = guess_letter
                if guess_letter in game_state.loose_letters:
                    game_state.loose_letters.remove(guess_letter)

        # Create a pool of remaining letters to match against
        goal_letters = [l for l in goal_word]
        guess_letters = [l for l in guess_word]
        for i, found_letter in enumerate(game_state.found_letters):
            if found_letter != None:
                goal_letters.remove(found_letter)
                if guess_word[i] == found_letter:
                    guess_letters.remove(found_letter)

        # Remove the existing letters from the loose pool to avoid repeats
        for l in guess_letters:
            if l in game_state.loose_letters:
                game_state.loose_letters.remove(l)

        # Search for loose letters, move them from the goal word into
        # the loose letter pool
        for l in guess_letters:
            if l in goal_letters:
                game_state.loose_letters.append(l)
                goal_letters.remove(l)

        # Add uniquely invalid letters to the invalid pool
        for l in guess_word:
            if l not in goal_word:
                game_state.invalid_letters.add(l)
    return turn


def check_word(word, game_state):
    # Has the word already been guessed?
    if word in game_state.guesses:
        return False

    # Does the word contain invalid letters?
    for l in word:
        if l in game_state.invalid_letters:
            return False

    # Are all the found letters in the correct spot?
    for wl, fl in zip(word, game_state.found_letters):
        if fl != None and fl != wl:
            return False

    # Create a pool of remaining letters to match against
    guess_letters = [l for l in word]
    for i, found_letter in enumerate(game_state.found_letters):
        if found_letter != None:
            if word[i] == found_letter:
                guess_letters.remove(found_letter)

    # Are ALL loose letters contained within the remaining letters?
    for l in game_state.loose_letters:
        if l in guess_letters:
            # If there are two of the same letter, there need to be two in the word as well
            guess_letters.remove(l)
        else:
            return False

    return True


def get_valid_words(game_state):
    return [word for word in words if check_word(word, game_state)]


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


def pick_best_word_v1(game_state):
    """
    Pick the best word based on global letter scores.  
    Picks the highest scoring word that is still possible and hasn't already been guessed
    Only provides valid guesses
    """
    return next(word for word in sorted_words if check_word(word, game_state))
    # for word in sorted_words:
    #     if check_word(word, game_state):
    #         return word


def pick_best_word_v2(game_state):
    """
    Same as V1 but recalculates letter scores based on the remaining words
    1. Get all the remaining valid words
    2. Recalculate letter scores for the remaining letters
    Only provides valid guesses
    """
    valid_words = get_valid_words(game_state)
    letter_score = get_letter_scores(valid_words)
    return max((word for word in valid_words),
               key=lambda word: get_word_score(word, letter_score))


def pick_best_word_v3(game_state):
    """
    Picks a guess based on the following heuristic
    1. Use found spaces to explore remaining letters. Remaining letters should (preferrably) be explored
       in the order of their prevalence in the remaining words.
    2. Explore new positions for loose letters. This heuristic should stop us from getting stuck in loops
       when an anagram is found.
    """
    pass


def evaluate_strategy(strategy):
    word_difficulty = Parallel(n_jobs=16)(delayed(play_game)(
        goal_word=word, input_source=strategy) for word in tqdm(words))
    difficulty_spread = Counter(word_difficulty)
    average_turns = sum(word_difficulty) / len(words)
    num_solved = len(
        [turn_count for turn_count in word_difficulty if turn_count <= 6])
    print(f"{difficulty_spread=}")
    print(f"{average_turns=}")
    print(f"{num_solved=} ({num_solved / len(words) * 100:.1f}%)")


# play_game("slump", pick_best_word_v1, print)

print("V1")
evaluate_strategy(pick_best_word_v1)

print("V2")
evaluate_strategy(pick_best_word_v2)

# print("V3")
# evaluate_strategy(pick_best_word_v3)
