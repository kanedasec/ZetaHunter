import re
import ast
import textwrap
from typing import Tuple, List

PROHIBITED_PATTERNS = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\bPopen\b",
    r"\bsocket\b",
    r"\bpty\b",
    r"\beval\b",
    r"\bexec\b",
    r"\bcompile\b",
    r"\bopen\s*\(",          # bloqueia escrita/leitura de arquivo (ajuste se quiser permitir 'r')
    r"\bimportlib\b",
    r"\bctypes\b",
    r"\bfork\b",
]

# ---------- helpers de limpeza ----------

def _strip_code_fences(s: str) -> str:
    """Remove cercas Markdown ``` ``` (incl. ```python)."""
    if not s:
        return s
    # remove uma cerca de abertura típica na 1a linha
    s = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*\r?\n", "", s)
    # remove uma cerca de fechamento no fim
    s = re.sub(r"\r?\n```[ \t]*\r?\n?\s*$", "\n", s)
    # remove quaisquer blocos cercados remanescentes
    s = re.sub(r"```(?:.|\n)*?```", lambda m: m.group(0).replace("```", ""), s)
    return s.strip()

def _extract_python_from_python_c(s: str) -> str:
    """
    Se o LLM retornou algo como:  python -c "print('oi')"
    extrai o conteúdo interno.
    """
    m = re.search(r"""python\s+-c\s+(['"])(.*)\1\s*$""", s.strip(), flags=re.S)
    if m:
        payload = m.group(2)
        try:
            payload = payload.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass
        return payload
    return s

def _strip_triple_quotes_wrappers(s: str) -> str:
    s = s.strip()
    if (s.startswith('"""') and s.endswith('"""')) or (s.startswith("'''") and s.endswith("'''")):
        return s[3:-3].strip()
    return s

# ---------- detecção / regras ----------

def _detect_prohibited(s: str) -> List[str]:
    warns: List[str] = []
    for pat in PROHIBITED_PATTERNS:
        if re.search(pat, s):
            warns.append(f"prohibited pattern detected: {pat}")
    return warns

def _enforce_single_json_print(s: str) -> List[str]:
    """
    Regras rígidas de saída:
    - deve haver "import json" (qualquer lugar do arquivo);
    - deve existir exatamente UM print(...);
    - esse print deve envolver json.dumps(...).
    """
    problems: List[str] = []

    has_json_import = re.search(r"^\s*import\s+json\b", s, flags=re.M) is not None
    if not has_json_import:
        problems.append("script must import json")

    # captura prints simples linha-a-linha (não pega prints multilinha complexos; bom o suficiente p/ PoC curta)
    prints = re.findall(r"^\s*print\s*\(.*\)\s*$", s, flags=re.M)
    if len(prints) != 1:
        problems.append("script must contain exactly one print(...)")

    # verifique se o único print contém json.dumps(
    if len(prints) == 1 and "json.dumps" not in prints[0]:
        problems.append("print(...) must be print(json.dumps(...))")

    return problems

def sanitize_and_validate_script(script_text: str) -> Tuple[str, bool, List[str]]:
    """
    Retorna (sanitized_script, ok_to_save_and_run, warnings)
    - sanitized_script: código limpo/dedented (string possivelmente vazia em erro grave)
    - ok_to_save_and_run: True se não há padrões críticos proibidos e passou em validações
    - warnings: lista de mensagens explicando problemas (inclui erros de sintaxe/validação)
    """
    warnings: List[str] = []
    if script_text is None:
        return ("", False, ["empty script"])

    # 1) normalizações
    s = script_text
    s = _strip_code_fences(s)
    s = _extract_python_from_python_c(s)
    s = _strip_triple_quotes_wrappers(s)
    s = textwrap.dedent(s).strip()

    if len(s) == 0:
        return ("", False, ["script empty after removing fences/containers"])

    # 2) padrões proibidos (crítico)
    warnings.extend(_detect_prohibited(s))

    # 3) validação de sintaxe inicial
    try:
        compile(s, "<generated_script>", "exec")
    except SyntaxError as se:
        warnings.append(f"syntax error: {se.msg} at line {se.lineno}")
        return (s, False, warnings)
    except Exception as e:
        warnings.append(f"parse error: {e}")
        return (s, False, warnings)

    # 4) AST leve (apenas avisos)
    try:
        tree = ast.parse(s)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.split(".")[0] in {"os", "subprocess", "socket", "pty", "ctypes", "importlib"}:
                        warnings.append(f"import of suspicious module: {name}")
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"eval", "exec", "compile"}:
                warnings.append(f"call to suspicious builtin: {getattr(node.func, 'id', '')}")
    except Exception:
        # não quebra se AST falhar, já passamos por compile
        pass

    # 5) exige exatamente um print(json.dumps(...)) e import json
    rigid_out_problems = _enforce_single_json_print(s)
    if rigid_out_problems:
        warnings.extend(rigid_out_problems)
        return (s, False, warnings)

    # 6) decisão final
    critical = any("prohibited pattern detected" in w for w in warnings)
    ok = not critical and len(rigid_out_problems) == 0
    return (s, ok, warnings)

# --- Compatibilidade antiga: algumas partes podem esperar scan_script() que retorna (ok, warnings)
def scan_script(script_text: str):
    sanitized, ok, warnings = sanitize_and_validate_script(script_text)
    return ok, warnings
