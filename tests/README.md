# Test Pack for aaf2resolve-spec Validation

This directory contains JSON samples used to validate the canonical schema and ensure spec compliance.

## 📁 Structure

```
tests/
├── samples/           # JSON test files
│   ├── minimal_valid.json
│   ├── invalid_missing_keys.json
│   └── ... (add more as needed)
└── README.md         # This file
```

## ✅ Current Test Samples

### `minimal_valid.json`
- **Purpose:** Minimal valid canonical JSON that should pass all validations
- **Expected:** ✅ 0 errors, all schema checks pass
- **Contains:** Basic project + timeline + single event with source

### `invalid_missing_keys.json` 
- **Purpose:** Deliberately invalid JSON to test error detection
- **Expected:** ❌ Multiple validation failures
- **Expected codes:** 
  - `CANON-REQ-006` (missing tc_format)
  - `CANON-REQ-020` (invalid event ID format)
  - `CANON-REQ-037` (keyframes not time-ordered)
  - `CANON-REQ-028` (empty UMID in chain)

## 🔄 How Validation Works

The **Orchestrator Space** automatically discovers all `tests/samples/*.json` files and runs validation against:

1. **JSON Schema** - Structure, types, required keys per `docs/data_model_json.md`
2. **Additional Rules** - Custom validations not expressible in JSON Schema
3. **Reason Codes** - Structured error reporting with traceable codes

## ➕ Adding New Test Samples

To add a new validation test:

1. **Create JSON file** in `tests/samples/` with descriptive name:
   ```
   tests/samples/your_test_case.json
   ```

2. **Document expected behavior** (add to this README):
   - Purpose of the test
   - Expected pass/fail status  
   - Expected reason codes (if failing)

3. **Run validation** via Orchestrator Space:
   - Single sample: Use dropdown in "Run validator on single sample"
   - All samples: Click "🚀 Run validator on all samples"

4. **Verify results** in validation reports and summary badge

## 🧭 Integration with Orchestrator

- **Auto-discovery:** Orchestrator batch runner picks up any `*.json` files here automatically
- **Summary badge:** Shows ✅ All passing (N) or ❌ K failing of N based on latest results  
- **Reports:** Individual timestamped reports written to `reports/validation/`
- **Git integration:** All validation runs automatically commit and push results

## 📊 Validation Report Structure

Each validation generates a report with:

```json
{
  "ok": true|false,
  "errors": [
    {
      "code": "CANON-REQ-XXX", 
      "path": "$.timeline.events[0].id",
      "message": "Specific error description",
      "doc": "docs/data_model_json.md"
    }
  ],
  "summary": {
    "checked": 4,
    "failed": 1, 
    "reason_codes": ["CANON-REQ-006"]
  }
}
```

## 🎯 Best Practices

- **Descriptive names:** Use clear filenames that indicate test purpose
- **Focused tests:** Each file should test specific validation rules
- **Document expectations:** Always note expected pass/fail status and error codes
- **Minimal examples:** Keep test JSONs as simple as possible while covering the target case

---

*This test pack is automatically processed by the Orchestrator Space. Changes to samples trigger new validation runs and update the summary badge.*
