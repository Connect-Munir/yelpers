# N8N Custom Skills Reference

This directory contains 7 specialized skills for building n8n workflows with Claude Code.

## Skills Overview

### 1. **n8n-code-javascript**
**Master JavaScript in n8n Code nodes**

Use when:
- Writing custom logic in Code nodes
- Accessing data with $input, $json, $node
- Making HTTP requests with $helpers
- Transforming and filtering data
- Working with dates using DateTime

Key Topics:
- Input data access patterns
- HTTP request helpers
- Common JavaScript patterns
- Data transformation examples
- Error handling and best practices

📍 Location: `.claude/skills/n8n-code-javascript/skill.md`

---

### 2. **n8n-code-python**
**Write Python code in n8n Code nodes**

Use when:
- Need regex or text processing
- Statistical analysis or math operations
- Using Python standard library (hashlib, statistics, collections)
- Task requires Python-specific functionality
- User explicitly prefers Python

Key Topics:
- Input data access patterns
- Available standard libraries
- Known limitations
- Common patterns and examples
- Performance considerations

📍 Location: `.claude/skills/n8n-code-python/skill.md`

---

### 3. **n8n-expression-syntax**
**Master {{ }} expression syntax**

Use when:
- Writing expressions to map data between nodes
- Accessing values from previous nodes
- Building conditional logic
- String interpolation in URLs/messages
- Debugging expression errors

Key Topics:
- Basic syntax and variable access
- Conditional logic patterns
- Array and object methods
- Date/time operations
- Type checking and null coalescing
- Common mistakes and debugging

📍 Location: `.claude/skills/n8n-expression-syntax/skill.md`

---

### 4. **n8n-mcp-tools-expert**
**Expert guide to MCP tools**

Use when:
- Searching for specific nodes
- Validating node configurations
- Finding template workflows
- Understanding node properties
- Planning workflow architecture

Key Topics:
- search_nodes — Find candidate nodes
- get_node — Get detailed node information
- search_templates — Find reference workflows
- validate_node — Check configuration
- validate_workflow — Validate workflow structure
- Tool usage patterns and best practices

📍 Location: `.claude/skills/n8n-mcp-tools-expert/skill.md`

---

### 5. **n8n-node-configuration**
**Operation-aware node configuration**

Use when:
- Setting up node properties
- Understanding property dependencies
- Choosing operation for a node
- Configuring authentication
- Understanding display options

Key Topics:
- Node categories and types
- Operation patterns (List, Get, Create, Update, Delete)
- Required vs optional properties
- Display options and conditions
- Property type reference
- Common configuration errors

📍 Location: `.claude/skills/n8n-node-configuration/skill.md`

---

### 6. **n8n-validation-expert**
**Interpret and fix validation errors**

Use when:
- Workflow shows validation errors
- Understanding what errors mean
- Fixing validation warnings
- Testing expressions
- Preventing validation loops

Key Topics:
- Common error messages and fixes
- Warning vs error distinction
- Expression validation
- False positives
- Validation checklist
- Debugging unclear errors

📍 Location: `.claude/skills/n8n-validation-expert/skill.md`

---

### 7. **n8n-workflow-patterns**
**Proven architectural patterns**

Use when:
- Designing workflow architecture
- Choosing between design approaches
- Building complex workflows
- Implementing error handling
- Structuring data processing

10 Core Patterns:
1. **Request-Transform-Response** — API integrations, ETL
2. **Conditional Branching** — Different paths based on conditions
3. **Loop Processing** — Handle multiple items
4. **Error Handling & Retry** — Resilient workflows
5. **Data Aggregation & Merge** — Combine multiple sources
6. **Scheduled Tasks & Polling** — Regular maintenance tasks
7. **Webhook Listener** — Event-driven workflows
8. **Modular Sub-Workflows** — Reusable components
9. **Caching & Rate Limiting** — Optimized API usage
10. **Data Transformation Pipeline** — Complex ETL

📍 Location: `.claude/skills/n8n-workflow-patterns/skill.md`

---

## How to Use These Skills

### During Workflow Development

**When building a workflow:**
1. Start with **workflow-patterns** to choose architecture
2. Use **mcp-tools-expert** to search for and understand nodes
3. Use **node-configuration** to set up each node's properties
4. Use **expression-syntax** when mapping data between nodes
5. Use **code-javascript** or **code-python** for custom logic
6. Use **validation-expert** to fix any validation errors
7. Test and iterate

### Example: Building an Email Notification Workflow

```
1. Use workflow-patterns
   → Choose "Request-Transform-Response" pattern
   
2. Use mcp-tools-expert
   → search_nodes("email") → Find email providers
   → search_templates("send email") → See examples
   
3. Use node-configuration
   → Get details on required properties
   → Understand authentication options
   
4. Use expression-syntax
   → Map order data to email template
   → Build dynamic subject line
   
5. Use validation-expert
   → Fix any validation errors
   → Check configuration
   
6. Deploy and test
```

### When Troubleshooting

**If workflow has errors:**
1. Check with **validation-expert** skill
2. Review node setup with **node-configuration**
3. Fix expressions with **expression-syntax**
4. For code errors, use **code-javascript** or **code-python**
5. Validate final workflow structure

### When Learning N8N

**To improve your n8n skills:**
- Read through each skill's key topics
- Study the examples and patterns
- Reference skills while building
- Use skills to understand errors
- Build incrementally, consulting skills as needed

---

## Accessing Skills

### In Claude Code
Each skill is automatically available during workflow development. They activate based on context:
- Writing expressions? → **expression-syntax** engages
- Configuring nodes? → **node-configuration** engages
- Validation errors? → **validation-expert** engages
- Designing architecture? → **workflow-patterns** engages
- Writing code? → **code-javascript** or **code-python** engages
- Selecting nodes? → **mcp-tools-expert** engages

### Direct Reference
You can explicitly reference any skill:
- "Help me write JavaScript for this Code node"
- "What's the validation error mean?"
- "Show me a pattern for this use case"
- "How do I configure this node?"

---

## Skill Index by Use Case

| Use Case | Skills to Reference |
|----------|-------------------|
| Build API integration | patterns, mcp-tools-expert, node-config, validation-expert |
| Write custom code | code-javascript, code-python, expression-syntax |
| Debug validation errors | validation-expert, expression-syntax, node-config |
| Design workflow | workflow-patterns, mcp-tools-expert |
| Configure node | node-configuration, mcp-tools-expert, validation-expert |
| Map data | expression-syntax, code-javascript |
| Handle errors | workflow-patterns (error handling pattern) |
| Optimize performance | workflow-patterns (caching/rate limit pattern) |
| Process data | workflow-patterns (transformation pattern), code-javascript |
| Schedule task | workflow-patterns (scheduled task pattern) |

---

## File Structure

```
.claude/skills/
├── n8n-code-javascript/
│   └── skill.md
├── n8n-code-python/
│   └── skill.md
├── n8n-expression-syntax/
│   └── skill.md
├── n8n-mcp-tools-expert/
│   └── skill.md
├── n8n-node-configuration/
│   └── skill.md
├── n8n-validation-expert/
│   └── skill.md
├── n8n-workflow-patterns/
│   └── skill.md
└── README.md (this file)
```

---

## Quick Reference

### Expression Syntax Quick Guide
```
$json.fieldName               → Access current item field
$node['Node Name'].json       → Access another node's output
{{expression}}                → Use expressions in fields
$json.field ?? 'default'      → Null coalescing
`Hello ${$json.name}`         → Template literals
```

### Common Code Patterns
**JavaScript:**
```javascript
const items = $input.all();
return items.map(item => ({...item.json, new_field: 'value'}));
```

**Python:**
```python
items = _input.all()
return [dict({**item.json, 'new_field': 'value'}) for item in items]
```

### Node Types
- **Trigger:** Webhook, Schedule, Manual
- **Action:** HTTP, Email, Database, API integrations
- **Transform:** Set, Code, Merge, Function
- **Control:** If, Loop, For Each, SplitInBatches

### Validation Workflow
1. If error → Check validation-expert
2. Fix issue
3. Validate again
4. Continue building

---

## Tips for Success

1. **Start Simple** — Begin with simple patterns, build complexity gradually
2. **Use Templates** — Reference similar workflows from search_templates
3. **Test Early** — Validate configuration as you build
4. **Handle Errors** — Always include error handling in production
5. **Document** — Add notes to complex sections
6. **Reuse Code** — Extract common logic to sub-workflows
7. **Monitor** — Log important events for debugging
8. **Iterate** — Build incrementally, testing each section

---

## When to Consult Each Skill

| Skill | Consult When... |
|-------|-----------------|
| JavaScript | Writing { code in Code nodes, need data transformation |
| Python | Need regex, statistics, or Python stdlib |
| Expression Syntax | Mapping data between nodes, building conditions |
| MCP Tools Expert | Searching for nodes, understanding node properties |
| Node Configuration | Setting up node properties, understanding dependencies |
| Validation Expert | Fixing validation errors, understanding warnings |
| Workflow Patterns | Designing architecture, choosing approach |

---

## Related Resources

- **CLAUDE.md** — Project guidelines and best practices
- **.mcp.json** — MCP server configuration
- **.claude/settings.json** — Project settings
- **N8n Dashboard** — http://localhost:5678 (your instance)

---

## Next Steps

Ready to build? Start with:
1. Define your workflow goal
2. Check **workflow-patterns** for matching architecture
3. Use **mcp-tools-expert** to find nodes
4. Reference **node-configuration** as you build
5. Validate with **validation-expert**
6. Deploy and test

Questions? Consult the relevant skill or reference this README.

**Happy workflow building! 🚀**
