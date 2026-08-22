# Agentic Threats and Automation

Attackers increasingly use AI and automation to scan, adapt, and act faster than a human operator could alone.

## Autonomous attacker capabilities
- LLM-driven reconnaissance and service fingerprinting
- automated exploit chaining across multiple hosts
- AI-generated phishing personalized and produced at scale
- self-directed lateral movement decision-making

## Prompt injection as an attack technique
- instructions hidden in scanned content, logs, or documents meant for an AI analyst
- indirect injection: an agent later retrieves attacker-planted content and treats it as trustworthy

## Knowledge-base / RAG poisoning
- an attacker plants misleading, authoritative-looking documents into a shared knowledge base ahead of time
- retrieval later surfaces the poisoned content as if it were vetted
- defenders must treat retrieved content as evidence, not instruction

## Tool-use / function-calling abuse
- an agent with tool access can be manipulated into calling tools with attacker-chosen arguments if untrusted content is treated as a command

## Velocity and automation as a detection signal
- sub-second or millisecond-interval request timing
- unnaturally regular inter-event intervals (bot regularity vs. human jitter)
- breadth-before-depth scanning patterns
- off-hours mass activity

Students should learn to read timing and regularity as evidence in their own right — not just technique.
