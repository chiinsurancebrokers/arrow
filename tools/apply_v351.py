from pathlib import Path

p = Path("frontend/index.html")
text = p.read_text(encoding="utf-8")

cloudflare = '<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script>'
text = text.replace(cloudflare, "")

old = """                if (!res.ok) {
                    let detail = '';
                    try { detail = (await res.json()).detail || ''; } catch (_) { /* body wasn't JSON */ }
                    throw new Error('HAL request failed (' + res.status + ')' + (detail ? ': ' + detail : ''));
                }"""

new = """                if (!res.ok) {
                    let detail = '';
                    try {
                        const payload = await res.json();
                        const raw = payload && payload.detail;
                        if (typeof raw === 'string') {
                            detail = raw;
                        } else if (Array.isArray(raw)) {
                            detail = raw.map(item => {
                                const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
                                return (loc ? loc + ': ' : '') + (item.msg || JSON.stringify(item));
                            }).join('; ');
                        } else if (raw) {
                            detail = JSON.stringify(raw);
                        }
                    } catch (_) { /* body wasn't JSON */ }
                    throw new Error('HAL request failed (' + res.status + ')' + (detail ? ': ' + detail : ''));
                }"""

if old not in text:
    raise SystemExit("Expected HAL error-handling block not found; index.html was not patched.")
text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("Patched frontend/index.html:")
print("- removed obsolete Cloudflare email decoder")
print("- improved HAL validation/error detail formatting")
