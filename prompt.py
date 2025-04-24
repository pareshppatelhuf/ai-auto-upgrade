import os
import openai
import anthropic

# Step 1: Configuration
# or directly set your key here

# Step 2: Prepare prompt for AI
def create_prompt(file_content, file_name, old_version, new_version, artifact):
    return f"""
You are a coding assistant.

You are provided with a Java file {file_name} using dependency {artifact["group"]+":"+artifact["artifact"]} version {old_version}.

Your task is to:
- Update the code to be compatible with {artifact["group"]+":"+artifact["artifact"]} version {new_version}.
- Fix any breaking changes due to the version upgrade.
- Keep all other logic intact.

Respond ONLY with the updated file content.

Here is the original content:
{file_content}"""


def get_updated_file_content(file_path, prompt_data, client):  
    
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4096,
        temperature=0.3,
        system="You are a Java refactoring assistant.",
        messages=[
            {"role": "user", "content": prompt_data}
        ]
    )

    updated_code = response.content[0].text.strip()


    # Optional: Save to a new file or overwrite
    # new_filepath = filepath.replace(".java", f"_updated.java")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_code)