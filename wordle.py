import random

from tqdm import tqdm
from collections import Counter, namedtuple

# Get the master list of words
with open("words.txt", mode='r') as f:
    words = f.readlines()
words = [word.strip() for word in words]

def get_letter_scores(words):
    all_letters = (letter for word in words for letter in word)
    return Counter(all_letters)

def get_word_score(word, letter_score):
    return sum(letter_score[letter] for letter in set(word))

global_letter_score = get_letter_scores(words)
global_word_score = {word: get_word_score(word, global_letter_score) for word in words}
sorted_words = sorted(global_word_score, key=global_word_score.get, reverse=True)

# Calculate the number of turns it takes to get to word from start
def play_game(goal_word, input_source, display=lambda _="": ()):
    turn = 0
    found_letters = [None] * 5
    loose_letters = []
    invalid_letters = set()
    guesses = []
    while turn < 1000:
        turn += 1

        # Print the current state
        display("".join(l if l else "-" for l in found_letters))
        display(f"Loose letters: {loose_letters}")
        display(f"Invalid letters: {invalid_letters}")

        # Make a guess
        guess_word = input_source(found_letters, loose_letters, invalid_letters, guesses)
        guesses.append(guess_word)
        display(f"Guessed {guess_word}")
        if guess_word == goal_word:
            display(f"The word was {goal_word}!")
            return turn
        display()

        # Find exact matches
        for i, (guess_letter, goal_letter) in enumerate(zip(guess_word, goal_word)):
            if guess_letter == goal_letter:
                found_letters[i] = guess_letter
                if guess_letter in loose_letters:
                    loose_letters.remove(guess_letter)
        
        # Create a pool of remaining letters to match against
        goal_letters = [l for l in goal_word]
        guess_letters = [l for l in guess_word]
        for i, found_letter in enumerate(found_letters):
            if found_letter != None:
                goal_letters.remove(found_letter)
                if guess_word[i] == found_letter:
                    guess_letters.remove(found_letter)
        
        # Remove the existing letters from the loose pool to avoid repeats
        for l in guess_letters:
            if l in loose_letters:
                loose_letters.remove(l)

        # Search for loose letters, move them from the goal word into
        # the loose letter pool
        for l in guess_letters:
            if l in goal_letters:
                loose_letters.append(l)
                goal_letters.remove(l)
        
        # Add uniquely invalid letters to the invalid pool
        for l in guess_word:
            if l not in goal_word:
                invalid_letters.add(l)
    return turn


def check_word(word, found_letters, loose_letters, invalid_letters):
    # Does the word contain invalid letters?
    for l in word:
        if l in invalid_letters:
            return False
    
    # Are all the found letters in the correct spot?
    for wl, fl in zip(word, found_letters):
        if fl != None and fl != wl:
            return False

    # Create a pool of remaining letters to match against
    guess_letters = [l for l in word]
    for i, found_letter in enumerate(found_letters):
        if found_letter != None:
            if word[i] == found_letter:
                guess_letters.remove(found_letter)
    
    # Are ALL loose letters contained within the remaining letters?
    for l in loose_letters:
        if l in guess_letters:
            # If there are two of the same letter, there need to be two in the word as well
            guess_letters.remove(l)
        else:
            return False
    
    return True

# difficulty_spread=Counter({4: 1549, 5: 1456, 6: 902, 3: 753, 7: 489, 8: 272, 9: 139, 2: 97, 10: 59, 11: 25, 12: 8, 13: 5, 14: 1, 1: 1, 15: 1})
def pick_best_word_v1(found_letters, loose_letters, invalid_letters, guesses):
    for word in sorted_words:
        if word in guesses:
            continue
        if check_word(word, found_letters, loose_letters, invalid_letters):
            return word

# The goal should actually be to pick a guess based on the maximum number of words that can be ruled out
# 1. Get all the remaining valid words
# 2. Recalculate letter scores for the remaining letters
# 3. A good guess should:
#       a. Use found spaces to explore remaining letters. Remaining letters should (preferrably) be explored
#          in the order of their prevalence in the remaining words.
#       b. Explore new positions for loose letters. This heuristic should stop us from getting stuck in loops
#          when an anagram is found.
def pick_best_word_v2(found_letters, loose_letters, invalid_letters, guesses):
    valid_words = [word for word in words 
        if check_word(word, found_letters, loose_letters, invalid_letters) 
        and word not in guesses]
    letter_score = get_letter_scores(valid_words)
    return max((word for word in words if word not in guesses), 
        key=lambda word: get_word_score(word, letter_score))

def evaluate_strategy(strategy):
    word_difficulty = {word:play_game(goal_word=word, input_source=strategy) for word in tqdm(words)}
    difficulty_spread = Counter(word_difficulty.values())
    average_turns = sum(turns * count for turns, count in difficulty_spread.items()) / len(words)
    print(f"{difficulty_spread=}")
    print(f"{average_turns=}")

print("V1")
evaluate_strategy(pick_best_word_v1)

print("V2")
evaluate_strategy(pick_best_word_v2)