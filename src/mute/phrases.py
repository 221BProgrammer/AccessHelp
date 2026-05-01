import json
import os

class PhraseManager:
    def __init__(self, file_path="phrases.json"):
        self.file_path = file_path
        
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def load_phrases(self):
        with open(self.file_path, "r") as f:
            return json.load(f)

    def save_phrase(self, phrase):
        phrases = self.load_phrases()
        phrases.append(phrase)

        with open(self.file_path, "w") as f:
            json.dump(phrases, f)

    def delete_phrase(self, phrase):
        phrases = self.load_phrases()
        phrases.remove(phrase)

        with open(self.file_path, "w") as f:
            json.dump(phrases, f)