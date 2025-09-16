# Code Review Guidelines

This document outlines the code review process and guidelines for the PrisMind project.

## Review Process

1. **Pull Request Creation**
   - Create a feature branch from `develop`
   - Keep PRs small and focused (300-500 lines max)
   - Reference any related issues
   - Update documentation as needed

2. **Review Request**
   - Assign at least one reviewer
   - Add appropriate labels
   - Use the PR template
   - Ensure all CI checks pass

3. **Review Process**
   - Review within 24 hours of assignment
   - Provide constructive feedback
   - Use GitHub's suggestion feature when possible
   - Mark conversations as resolved when addressed

## Review Checklist

### Code Quality
- [ ] Code follows style guidelines
- [ ] No commented-out code
- [ ] No debug statements
- [ ] Proper error handling
- [ ] Logging is appropriate

### Functionality
- [ ] Changes work as expected
- [ ] Edge cases are handled
- [ ] No performance regressions
- [ ] Backward compatibility maintained

### Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Test coverage maintained/increased
- [ ] Manual testing steps documented

### Security
- [ ] No hardcoded secrets
- [ ] Input validation in place
- [ ] Authentication/authorization checks
- [ ] Dependencies are up-to-date

## Best Practices

### For Authors
- Keep commits atomic
- Write clear commit messages
- Address all review comments
- Update documentation
- Squash fixup commits

### For Reviewers
- Be respectful and constructive
- Focus on the code, not the author
- Explain the "why" behind suggestions
- Acknowledge good patterns

## Review Etiquette

### Do
- Ask clarifying questions
- Suggest alternatives
- Point out potential issues
- Acknowledge good solutions
- Be specific in feedback

### Don't
- Be dismissive
- Nitpick on style (use linters instead)
- Request changes without explanation
- Take feedback personally

## Review Labels

- `needs-tests`: Missing test coverage
- `needs-docs`: Missing documentation
- `bug`: Potential bug found
- `security`: Security concern
- `blocking`: Blocks merge
- `nit`: Minor, non-blocking issues

## Response Time Expectations

- First review: Within 24 hours
- Follow-up reviews: Within 12 hours
- Urgent PRs: Mark with `priority` label
- Blocked PRs: Update status regularly
