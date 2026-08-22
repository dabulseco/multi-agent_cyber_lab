# Prompt Injection and Model Risk

Prompt injection is the manipulation of model behavior through malicious or misleading instructions embedded in user content, retrieved content, or tools.

Students should evaluate:
- whether the model followed untrusted content as if it were policy
- whether the system separated trusted instructions from untrusted evidence
- whether the model leaked data or fabricated source support

Best practices:
- clearly separate system rules from retrieved content
- require evidence citations in outputs
- keep a human reviewer in the loop
