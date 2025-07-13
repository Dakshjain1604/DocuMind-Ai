import os
from dotenv import load_dotenv
load_dotenv()
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


from langchain_openai import ChatOpenAI
from routes.DocContent import DocContent

llm = ChatOpenAI(model="gpt-4o-mini",temperature=0.2)




async def summary(path, file_type):
    """Generate a rich, structured, and elaborated summary from file content"""

    prompt_summary = ChatPromptTemplate.from_messages([
        ("system", """
You are a top-level educator and expert summarizer. Your task is to read a document and generate a clear, deeply informative, and student-friendly summary. 
Focus on **clarity, structure, and completeness**, ensuring **each point is well-explained** — not just one-liners.

---

## ✨ Output Format (Strict Markdown)

### **Summary**

**Overview:**  
Write a clear 4–6 sentence paragraph explaining:
- What the document is about  
- Why it matters  
- What areas or topics it covers  
Keep it concise but rich enough to give immediate understanding.

---

### **Key Topics and Explanations**
Use subsections (`###`) for each major concept.  
For **each key topic**, provide:
- **Name of the topic/concept** (as subsection title)
- A **3–5 sentence explanation** in simple language
- If relevant, include important formulas or theorems and explain **what they mean and where they apply**

---

### **Critical Details**
List 4–6 bullet points, and for each:
- Write **2–3 sentence** explanations
- Include factual, technical, or structural insights from the source

---

### **Real-World Applications**
List **2–3 use cases** or examples that **apply the document's concepts**:
- For each, describe the context and how the concept helps solve a real problem  
- Each use case should be **3–5 sentences** long

---

## 🔒 Guidelines

- Use Markdown formatting strictly
- Use clear headers, bullet points, and paragraphs
- NEVER use one-liners unless summarizing a formula or definition
- Preserve original meaning — do not add external facts
- Summary should be around **5–10%** of the document length
- Keep language simple, but not shallow

---

Document to summarize:  
{context}
""")
    ])

    doc = DocContent(path, file_type)
    docs = [doc]

    chain = create_stuff_documents_chain(llm, prompt_summary)
    result = await chain.ainvoke({"context": docs})
    return result
