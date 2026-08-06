# Policy Rules

Rules are declarative and versioned.

## Fields

- `rule_id`
- `priority`
- `effect`
- `actors`
- `capabilities`
- `resources`
- `conditions`
- `requirements`
- `reason_code`

## Condition operators

- `equals`
- `not_equals`
- `in`
- `not_in`
- `contains`
- `exists`
- `greater_than`
- `less_than`

No arbitrary expressions, shell, or dynamic imports are allowed.

## Precedence

1. ERROR or invalid request
2. DENY rules
3. DEFER rules
4. CONFIRM rules
5. ALLOW rules
6. Default deny

Higher priority wins; ties broken by specificity then rule_id.
