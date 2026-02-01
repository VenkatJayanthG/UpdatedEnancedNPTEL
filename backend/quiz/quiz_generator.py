import json
import os
import requests


class QuizGenerator:
    def __init__(self, ollama_url="http://localhost:11434/api/generate", model="llama3"):
        self.ollama_url = ollama_url
        self.model = model

    def _get_transcript_text(self, youtube_id, watch_time):
        if not youtube_id:
            return None
            
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            transcript_list = None
            try:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(youtube_id)
                except:
                    pass
                
                if not transcript_list:
                    try:
                        transcript_list = YouTubeTranscriptApi().get_transcript(youtube_id)
                    except:
                        pass
                
                if not transcript_list:
                    try:
                        ts_obj = YouTubeTranscriptApi.list(youtube_id)
                        transcript_list = ts_obj.find_transcript(['en']).fetch()
                    except:
                        try:
                            ts_obj = YouTubeTranscriptApi().list(youtube_id)
                            transcript_list = ts_obj.find_transcript(['en']).fetch()
                        except:
                            pass
                
                if not transcript_list:
                    import youtube_transcript_api as yta
                    if hasattr(yta, 'get_transcript'):
                        transcript_list = yta.get_transcript(youtube_id)
            except Exception as e:
                print(f"Transcript strategies failed: {e}")

            if not transcript_list or not isinstance(transcript_list, list):
                return None

            relevant_text = []
            for entry in transcript_list:
                if isinstance(entry, dict) and 'start' in entry and 'text' in entry:
                    if entry['start'] <= watch_time:
                        relevant_text.append(entry['text'])
                    else:
                        break
            
            return " ".join(relevant_text) if relevant_text else None
        except Exception as e:
            print(f"Transcript service error: {e}")
            return None





    def generate_quiz(self, topic_id, topic_name, youtube_id, watch_time=0, difficulty="medium"):
        transcript_context = self._get_transcript_text(youtube_id, watch_time)
        
        context_prompt = ""
        if transcript_context:
            context_prompt = f"Use the following transcript context from the video (covering up to {watch_time} seconds) to generate questions specifically about this content:\n\n{transcript_context[:3000]}\n\n"
        else:
            context_prompt = f"Generate a quiz for the topic: {topic_name}. (Note: Transcript unavailable, use general knowledge about {topic_name})\n\n"

        prompt = f"""{context_prompt}
Generate a 3-question MCQ quiz.
Difficulty level: {difficulty}.

Return the result ONLY as a JSON object with this exact structure:
{{
    "topic_id": "{topic_id}",
    "difficulty": "{difficulty}",
    "questions": [
        {{
            "id": 1,
            "text": "Question text here?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Correct Option text exactly"
        }},
        {{
            "id": 2,
            "text": "Second question text?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Correct Option"
        }},
        {{
            "id": 3,
            "text": "Third question text?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Correct Option"
        }}
    ]
}}"""
        
        try:
            response = requests.post(self.ollama_url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }, timeout=90) 
            if response.status_code == 200:
                quiz_data = json.loads(response.json().get('response', '{}'))
                if quiz_data and 'questions' in quiz_data:
                    return quiz_data
        except requests.exceptions.ConnectionError:
            print("Ollama not running. Using fallback quiz.")
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return self._get_fallback_quiz(topic_id, topic_name, difficulty)


    def _get_fallback_quiz(self, topic_id, topic_name, difficulty):
        fallback = {
            "topic_id": topic_id,
            "difficulty": difficulty,
            "questions": [
                {
                    "id": 1,
                    "text": f"What is the primary concept covered in {topic_name}?",
                    "options": ["Fundamental principles", "Advanced techniques", "Historical context", "Practical applications"],
                    "answer": "Fundamental principles"
                },
                {
                    "id": 2,
                    "text": f"Which approach is best for understanding {topic_name}?",
                    "options": ["Sequential learning", "Random exploration", "Memorization only", "Skipping basics"],
                    "answer": "Sequential learning"
                },
                {
                    "id": 3,
                    "text": f"What skill does {topic_name} help develop?",
                    "options": ["Problem solving", "None", "Avoiding challenges", "Guessing"],
                    "answer": "Problem solving"
                }
            ]
        }
        self._save_to_bank(topic_id, fallback)
        return fallback


quiz_gen = QuizGenerator()
