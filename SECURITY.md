# Security Policy

## Supported Versions

We take security seriously and actively support only the latest stable version of Zapret Launcher. Older versions are not maintained and may contain unpatched vulnerabilities.

| Version | Supported | Status |
| ------- | --------- | ------ |
| 3.2.1.9 | ✅ | Actively supported, receives security updates |
| 3.2.1.5 and below | ❌ | Not supported, vulnerabilities may exist |

**Recommendation:** Always use the latest version. You can check for updates inside the launcher, on the official website, or in the GitHub repository.

---

## Reporting a Vulnerability

We appreciate your help in making Zapret Launcher safer. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do not** disclose the vulnerability publicly.
2. Share the discovered issue in the channel `t.me/zapret_technical` for direct communication with the developers.
3. Include in your report:
   - Description of the vulnerability
   - Affected version
   - Potential impact
   - Suggested fix (if you have one)

### What to Expect

| Stage | Timeframe | Description |
|-------|-----------|-------------|
| **Acknowledgment** | Within 24 hours | We will confirm receipt of your report |
| **Investigation** | 3–7 days | We will analyze and verify the issue |
| **Fix & Release** | As soon as possible | A fix will be prepared and a new version released |
| **Public Disclosure** | After fix is released | We will credit you (if you wish) in the changelog |

### Safe Harbor

We commit to:
- Not pursuing legal action against researchers who report vulnerabilities responsibly
- Not publicly disclosing your identity without your consent
- Providing credit for discoveries (if you wish)

### Scope

The following are **in scope**:
- **Zapret Launcher** application (all modules)
- Update mechanism
- **Telegram Proxy** implementation
- Configuration files (`config.json`)
- Network communication

The following are **out of scope**:
- Third-party dependencies (**WinDivert**, **zapret** core) — report to their respective maintainers
- Physical security
- Social engineering attacks

---

## Security Best Practices for Users

To ensure your safety while using Zapret Launcher:

1. **Always download from official sources**:
   - Official website: `https://zapret-launcher.ru`
   - GitHub: `https://github.com/tweenkedrage/zapret-launcher`
   - Never download from third-party sites

2. **Keep the launcher updated**:
   - Install updates as soon as they become available

3. **Protect your Telegram Proxy secret key**:
   - Treat your `config.json` as confidential data
   - Do not share your secret with untrusted parties

---

## Responsible Disclosure

We follow the principle of **responsible disclosure**:
- We will work with users to resolve issues
- We will coordinate public disclosure after the fix is released
- We will credit users who discover and report vulnerabilities

---

## Acknowledgments

We thank the users who help make Zapret Launcher more secure. Your contributions are valuable and appreciated.

---

## For Security-Related Inquiries:
- [**Technical Channel** ](https://t.me/zapret_technical)

---

- Last updated: *06/24/2026*
- © 2026 Zapret Launcher
