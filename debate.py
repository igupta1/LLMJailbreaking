import os
import time
import torch
import openai
from transformers import AutoModelForCausalLM, AutoTokenizer
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Set up OpenAI API key
openai_api_key = ""
openai.api_key = openai_api_key

class AIDebate:
    def __init__(self):
        self.chatgpt_model = "gpt-3.5-turbo"  # Using gpt-3.5-turbo for speed

        # Use a tiny model instead of Mistral for much faster performance
        self.local_model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # Only 1.1B parameters vs 7B
        self.local_model = None
        self.local_tokenizer = None
        
        # NEW: Conversation memory
        self.chatgpt_messages = []
        self.tinyllama_conversation = ""
        
        self.max_turns = 5
        
        # Token limits
        self.chatgpt_max_tokens = 500
        self.tinyllama_max_tokens = 500

    def setup_local_model(self):
        """Load a tiny local model for quick responses"""
        print(f"Loading {self.local_model_name}...")

        # Always use CPU for consistent performance
        device = "cpu"
        print(f"Using device: {device}")

        try:
            # Load the tiny model without using low_cpu_mem_usage
            self.local_model = AutoModelForCausalLM.from_pretrained(
                self.local_model_name,
                torch_dtype=torch.float16
                # Removed low_cpu_mem_usage=True
            )

            self.local_tokenizer = AutoTokenizer.from_pretrained(self.local_model_name)

            print("✅ Small model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise e

    def get_chatgpt_response(self, prompt):
        """Get a response from ChatGPT via API with conversation memory"""
        try:
            # Initialize messages with system message if this is the first turn
            if not self.chatgpt_messages:
                self.chatgpt_messages = [{"role": "system", "content": "You are ChatGPT. Keep your responses conversational and engaging. End with a question to continue the discussion."}]
            
            # Add the current prompt to the conversation history
            self.chatgpt_messages.append({"role": "user", "content": prompt})

            # Get response from OpenAI with full conversation history
            response = openai.chat.completions.create(
                model=self.chatgpt_model,
                messages=self.chatgpt_messages,
                temperature=0.7,
                max_tokens=self.chatgpt_max_tokens
            )
            
            assistant_response = response.choices[0].message.content
            
            # Add the assistant's response to the conversation history
            self.chatgpt_messages.append({"role": "assistant", "content": assistant_response})
            
            # Prevent history from getting too long (keep last 10 messages)
            if len(self.chatgpt_messages) > 11:  # system message + 10 turns
                self.chatgpt_messages = [self.chatgpt_messages[0]] + self.chatgpt_messages[-10:]

            return assistant_response
            
        except Exception as e:
            print(f"ChatGPT API Error: {e}")
            return "Sorry, I encountered an error. What do you think?"

    def get_local_model_response(self, prompt):
        """Get a response from local tiny model with conversation memory"""
        try:
            # First time, initialize the conversation with a helpful context
            if not self.tinyllama_conversation:
                self.tinyllama_conversation = "This is a conversation between a human and an AI assistant. The AI is helpful, respectful, and engaging.\n\n"
            
            # Add the latest exchange to the conversation history
            self.tinyllama_conversation += f"Human: {prompt}\nAssistant:"
            
            # Ensure conversation doesn't exceed token limit (keep roughly last 1000 chars)
            if len(self.tinyllama_conversation) > 1500:
                # Find a good breaking point - ideally after a complete turn
                cutoff = self.tinyllama_conversation[-1000:].find("Human:")
                if cutoff != -1:
                    self.tinyllama_conversation = "This is a continuation of a conversation.\n\n" + self.tinyllama_conversation[-1000+cutoff:]
                else:
                    self.tinyllama_conversation = "This is a continuation of a conversation.\n\n" + self.tinyllama_conversation[-1000:]
            
            # Tokenize the entire conversation
            inputs = self.local_tokenizer(self.tinyllama_conversation, return_tensors="pt")
            
            # Generate with parameters
            with torch.no_grad():
                outputs = self.local_model.generate(
                    inputs.input_ids,
                    max_new_tokens=self.tinyllama_max_tokens,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True
                )
            
            # Decode the full output
            full_output = self.local_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the assistant's new response
            response = full_output[len(self.tinyllama_conversation):].strip()
            
            # Update the conversation with the assistant's response
            self.tinyllama_conversation += f" {response}\n\n"
            
            # Add a question if there isn't one
            if "?" not in response:
                response += " What do you think about this?"
                # Update the stored conversation with the added question
                self.tinyllama_conversation = self.tinyllama_conversation[:-2] + " What do you think about this?\n\n"
            
            return response
            
        except Exception as e:
            print(f"Local model error: {e}")
            error_response = "I'm processing. What are your thoughts?"
            # Add the error response to the conversation
            self.tinyllama_conversation += f" {error_response}\n\n"
            return error_response

    def start_quick_debate(self, topic):
        """Start a quick debate between ChatGPT and local model with memory"""
        print("\n" + "="*40)
        print(f"Quick Debate on: {topic}")
        print("="*40 + "\n")
        
        # Reset conversation memory for a new debate
        self.chatgpt_messages = []
        self.tinyllama_conversation = ""

        # Set up local model if not already done
        if self.local_model is None:
            self.setup_local_model()
            
        # TinyLlama asks ChatGPT the user's input verbatim
        print("TinyLlama is asking ChatGPT your input verbatim...")
        
        # Send the user's input directly to ChatGPT without any modification
        print("ChatGPT is thinking...")
        chatgpt_response = self.get_chatgpt_response(topic)
        print(f"ChatGPT: {chatgpt_response}\n")

        # Quick debate for specified number of turns
        for i in range(self.max_turns):
            # Local model's turn
            print("TinyLlama is thinking...")
            local_response = self.get_local_model_response(chatgpt_response)
            print(f"TinyLlama: {local_response}\n")

            # ChatGPT's turn
            print("ChatGPT is thinking...")
            chatgpt_response = self.get_chatgpt_response(local_response)
            print(f"ChatGPT: {chatgpt_response}\n")

        print("="*40)
        print("Quick debate concluded!")
        print("="*40 + "\n")

def main():
    print("Ultra-Lightweight AI Debate: ChatGPT vs TinyLlama")
    print("Setting up for quick exchanges with minimal resources")
    print("---------------------------------------------------")

    debate = AIDebate()

    while True:
        topic = input("\nEnter a topic for quick AI debate (or 'exit' to quit): ")

        if topic.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        debate.start_quick_debate(topic)

        continue_choice = input("\nAnother debate? (y/n): ")
        if continue_choice.lower() not in ["y", "yes"]:
            print("Goodbye!")
            break

if __name__ == "__main__":
    main()