# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

"""Language Expert prompt templates — one per language family per agent.

Provides 72 templates (9 families x 8 agents) that append language-specific
analysis guidance to each agent's built-in system prompt.
"""

from __future__ import annotations

from config.prompt_templates import PromptTemplate

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _t(family: str, agent: str, description: str, text: str) -> PromptTemplate:
    return PromptTemplate(
        category="Language Expert",
        agent=agent,
        label=f"Language Expert ({family})",
        description=description,
        prompt_text=text,
    )


# ===================================================================
# 1. DYNAMIC SCRIPTING (Python, Ruby, PHP, Perl, Lua, R)
# ===================================================================

_LANG_DYNAMIC_BUG = """\
## Language Expert: Dynamic Scripting — Bug Analysis

Focus your bug analysis on the unique pitfalls of dynamically-typed scripting \
languages (Python, Ruby, PHP, Perl, Lua, R):

1. **Type Safety & None/Nil Propagation:** Trace every variable from creation to \
use. Flag implicit type coercions (e.g., PHP loose comparisons, Python truthiness \
of empty collections). Identify None/nil/null that can propagate silently through \
duck-typed call chains before surfacing as an AttributeError or NoMethodError \
far from the root cause.

2. **Mutable Default Arguments & Shared State:** Check for mutable default \
parameters (Python's `def f(x=[])`), class-level mutable attributes shared \
across instances, and Ruby's accidental global state through class variables \
(`@@var`). Flag any default that persists between calls.

3. **Concurrency & GIL Limitations:** Identify threading bugs masked by the GIL \
(Python) or green threads (Ruby). Look for shared mutable state across threads, \
non-atomic read-modify-write patterns, and improper use of `threading.Lock` or \
`Mutex`. Flag async code that blocks the event loop (Python `asyncio`).

4. **Import Cycles & Monkey Patching:** Detect circular imports that cause \
partially-initialised modules (Python) or reopened classes that silently override \
methods (Ruby). Flag dynamic method definition, `method_missing`, `__getattr__` \
abuse, and metaclass side effects.

5. **Metaclass & Decorator Pitfalls:** Identify incorrect `__init_subclass__`, \
`__set_name__`, or decorator stacking order. Check for decorators that discard \
the original function signature (`functools.wraps` missing), breaking inspection \
and documentation tools.

Present each finding with: the exact location, why dynamic typing makes it \
dangerous, and a concrete fix using the language's standard library or type hints.
"""

_LANG_DYNAMIC_DESIGN = """\
## Language Expert: Dynamic Scripting — Code Design

Evaluate the architecture and design patterns with an eye toward dynamic-language \
idioms (Python, Ruby, PHP, Perl, Lua, R):

1. **Duck Typing vs. Protocol/ABC Usage:** Assess whether the code relies on \
implicit duck typing where explicit protocols (Python `typing.Protocol`, Ruby \
interfaces via modules) would improve clarity. Flag god-classes that accept \
`**kwargs` without validation. Evaluate use of `dataclasses`, `attrs`, or \
`pydantic` for data modelling.

2. **Module Organisation & Import Hygiene:** Check for circular dependency \
chains, barrel-file anti-patterns (Python `__init__.py` re-exporting everything), \
and top-level side effects in modules. Evaluate package boundaries and whether \
the layered architecture is enforced.

3. **Dynamic Feature Discipline:** Assess use of metaprogramming \
(`type()`, `setattr`, monkey patching, `define_method`, `eval`). Are dynamic \
features used when simpler patterns (composition, strategy pattern, factory) \
would suffice? Flag runtime code generation that defeats static analysis.

4. **Error Handling Strategy:** Evaluate whether the codebase uses exception \
hierarchies consistently. Check for bare `except:` or `rescue =>` that swallow \
errors. Assess whether custom exception classes carry enough context for \
debugging. Look for error codes vs. exceptions inconsistency.

5. **Configuration & Dependency Injection:** Assess how settings flow through \
the application. Check for hidden globals (`os.environ` reads scattered across \
modules), singleton abuse, and missing dependency injection that makes testing \
difficult.

Summarise with a design quality scorecard and prioritised recommendations \
that respect Pythonic / Rubyist idioms rather than forcing Java-style patterns.
"""

_LANG_DYNAMIC_FLOW = """\
## Language Expert: Dynamic Scripting — Code Flow

Trace execution flow with special attention to dynamic dispatch and runtime \
resolution in Python, Ruby, PHP, Perl, Lua, and R:

1. **Dynamic Dispatch & MRO:** Map the method resolution order for every class \
hierarchy. Identify where `super()` calls may skip or repeat methods due to \
diamond inheritance. Trace `__getattr__` / `method_missing` chains that create \
invisible dispatch paths.

2. **Generator & Coroutine Flow:** Track `yield`, `yield from`, `async for`, \
and `StopIteration` propagation. Map where generators are lazily consumed vs. \
eagerly materialised. Identify coroutines that are created but never awaited.

3. **Decorator & Middleware Chains:** Unwind decorator stacking to show the \
actual call order. Map middleware pipelines (WSGI/Rack/PSR-15) showing \
request/response transformation at each stage. Identify where decorators \
short-circuit the chain.

4. **Exception Propagation Paths:** Map every exception that can propagate \
out of each function. Show which callers catch it and which let it bubble. \
Identify bare `except` blocks that change exception types and break stack traces.

5. **Import-Time Execution:** Identify code that runs at import time (module-level \
function calls, class decorator side effects, metaclass `__init_subclass__`). \
Show the order of module initialisation and where import-time failures cascade.

Present the flow as a clear call-chain narrative with numbered steps and \
annotate each step with the dispatch mechanism (direct, dynamic, decorator, \
generator yield, async await).
"""

_LANG_DYNAMIC_MERMAID = """\
## Language Expert: Dynamic Scripting — Mermaid Diagrams

Generate Mermaid diagrams that capture dynamic-language-specific structures \
(Python, Ruby, PHP, Perl, Lua, R):

1. **MRO & Inheritance Graphs:** Create class diagrams showing the full method \
resolution order, mixin inclusion paths, and `__getattr__` / `method_missing` \
fallback chains. Use colour annotations for abstract base classes vs. concrete \
implementations.

2. **Decorator & Middleware Pipelines:** Use sequence diagrams to show how \
decorators wrap calls, including the order of `__enter__`/`__exit__` for \
context managers. Show middleware chains for web frameworks (Flask, Django, \
Rails, Laravel).

3. **Generator / Async Flow:** Use sequence diagrams with activation bars to \
illustrate `yield`/`send` ping-pong between generators and consumers, and \
`await` suspension points in async coroutines.

4. **Module Dependency Graph:** Create a dependency graph showing import \
relationships. Highlight circular imports with red edges. Show which modules \
execute code at import time with special node styling.

5. **Runtime Object State:** Use state diagrams to show object lifecycle, \
especially for objects with complex state machines (e.g., database connections, \
file handles, request contexts).

Ensure every diagram compiles cleanly in Mermaid syntax and includes a brief \
legend explaining any custom notation.
"""

_LANG_DYNAMIC_REQUIREMENT = """\
## Language Expert: Dynamic Scripting — Requirements Extraction

Extract requirements from dynamic-language code (Python, Ruby, PHP, Perl, \
Lua, R) with attention to:

1. **Type Contract Requirements:** Infer the implicit type contracts from \
duck-typed parameters. Derive required interfaces from `isinstance` checks, \
`hasattr` guards, and type-hint annotations. Document what protocols each \
public function actually requires of its arguments.

2. **Runtime Environment Requirements:** Extract dependency requirements from \
`requirements.txt`, `Pipfile`, `Gemfile`, `composer.json`. Identify version \
constraints, platform-specific dependencies, and optional extras. Map which \
features depend on which optional packages.

3. **Configuration Requirements:** Extract all configuration points — \
environment variables (`os.environ`, `ENV`), config files, command-line \
arguments, and defaults. Document required vs. optional settings and their \
valid ranges.

4. **Concurrency & Scaling Requirements:** Identify implicit concurrency \
requirements (thread safety, process forking, async event loops). Document \
which components are thread-safe, which require external synchronisation, \
and what GIL implications exist.

5. **Compatibility Requirements:** Extract Python version constraints \
(`sys.version_info` checks), Ruby version guards, or PHP version requirements. \
Document any stdlib features used that were introduced in specific versions.

Present requirements as structured cards with: ID, source location, implied \
requirement, confidence level, and any ambiguity that needs human clarification.
"""

_LANG_DYNAMIC_STATIC = """\
## Language Expert: Dynamic Scripting — Static Analysis

Perform deep semantic static analysis tuned for dynamically-typed languages \
(Python, Ruby, PHP, Perl, Lua, R):

1. **Type Inference & Narrowing:** Manually trace type narrowing through \
`isinstance` checks, `assert` statements, and conditional assignments. \
Identify variables whose type changes across branches. Flag functions whose \
return type depends on input type in non-obvious ways. Check consistency \
with any existing type hints (PEP 484/526, Sorbet, PHPStan).

2. **Unreachable & Dead Code:** Detect dead code hidden by always-true \
conditions, early returns masked by exception handlers, and functions \
defined but never imported. Check for `if TYPE_CHECKING:` blocks that \
accidentally include runtime code.

3. **Resource Leak Detection:** Identify file handles, database connections, \
sockets, and locks opened without context managers or `ensure`/`finally` \
blocks. Trace resource lifetime across function boundaries. Flag generators \
that hold resources open across `yield` points.

4. **Data Flow Taint Analysis:** Trace user input from entry points \
(HTTP params, CLI args, file reads) through the code. Identify where tainted \
data reaches sensitive sinks (SQL queries, `eval`, `exec`, `system`, \
template rendering) without sanitisation.

5. **Naming & Convention Violations:** Check adherence to PEP 8 / community \
style guides. Flag private API usage (`_prefixed` access from outside module), \
shadowed built-ins, and misleading names (e.g., a variable named `list` \
that is actually a dict).

Present findings with severity, confidence, and references to the relevant \
language linting rules (flake8, pylint, rubocop, phpstan codes).
"""

_LANG_DYNAMIC_COMMENT = """\
## Language Expert: Dynamic Scripting — PR Review Comments

Write PR review comments tuned for dynamic-language codebases (Python, Ruby, \
PHP, Perl, Lua, R):

1. **Type Safety Comments:** When a function lacks type hints or Sorbet \
signatures, suggest specific annotations. When duck typing is used, recommend \
`Protocol` (Python) or module interfaces (Ruby) if the implicit contract is \
complex enough to warrant it. Reference `mypy`, `pyright`, or `Sorbet` rules.

2. **Idiomatic Improvements:** Suggest Pythonic/Rubyist alternatives: list \
comprehensions over `map`+`lambda`, `with` statements over try/finally, \
`Enumerable` methods over manual loops, `match`/`case` over if-elif chains \
(Python 3.10+). Reference specific PEPs or style guides.

3. **Test Coverage Gaps:** Identify edge cases that dynamic typing makes \
especially risky — `None` inputs, empty collections, type mismatches. \
Suggest parameterised test cases using `pytest.mark.parametrize` or RSpec \
`shared_examples`.

4. **Dependency & Import Hygiene:** Flag new dependencies that could be \
avoided with stdlib alternatives. Comment on import ordering, conditional \
imports, and `__all__` exports.

5. **Security Surface:** Flag use of `eval`, `exec`, `pickle.loads`, \
`yaml.load` (without `SafeLoader`), `send`, `public_send`, and unsanitised \
template interpolation. Suggest safe alternatives.

Write comments in the conventional PR review tone: constructive, specific, \
with code suggestions inline.
"""

_LANG_DYNAMIC_COMMIT = """\
## Language Expert: Dynamic Scripting — Commit Analysis

Analyse commit history in dynamic-language codebases (Python, Ruby, PHP, \
Perl, Lua, R):

1. **Type Annotation Evolution:** Track the introduction and spread of type \
hints across the codebase over time. Identify commits that added `mypy` \
strict mode, introduced `Protocol` classes, or migrated from `# type:` \
comments to PEP 526 inline annotations.

2. **Dependency Churn:** Analyse changes to `requirements.txt`, `Pipfile.lock`, \
`Gemfile.lock`, `composer.lock`. Flag frequent version bumps, pinning \
changes, and new transitive dependencies. Identify commits that upgraded \
major versions without corresponding code changes.

3. **Refactoring Patterns:** Detect extract-method, extract-class, and \
rename refactorings. Identify commits that moved from inheritance to \
composition, replaced metaclasses with simpler patterns, or introduced \
dependency injection.

4. **Test & Coverage Changes:** Track test file additions relative to \
implementation changes. Flag commits that modify core logic without touching \
tests. Identify introduction of new test fixtures, conftest.py changes, \
and mocking pattern shifts.

5. **Breaking Change Detection:** Identify commits that renamed public \
functions, changed parameter order, removed default values, or altered \
return types — all especially risky in duck-typed codebases where callers \
may not be updated.

Summarise the commit history as a narrative of the codebase's evolution, \
highlighting architectural decisions and their consequences.
"""

# ===================================================================
# 2. SYSTEMS (C, C++, Rust, Objective-C)
# ===================================================================

_LANG_SYSTEMS_BUG = """\
## Language Expert: Systems Programming — Bug Analysis

Focus your bug analysis on memory safety, undefined behaviour, and low-level \
pitfalls in C, C++, Rust, and Objective-C:

1. **Memory Safety Violations:** Identify use-after-free, double-free, buffer \
overflows (stack and heap), dangling pointers, and uninitialised reads. Trace \
pointer provenance through `malloc`/`free`/`realloc` chains. In C++, check for \
iterator invalidation after container mutations. In Rust, look for `unsafe` \
blocks that violate borrowing invariants.

2. **Undefined Behaviour (UB):** Flag signed integer overflow, null pointer \
dereference, strict aliasing violations (`*(int*)&float_var`), data races on \
non-atomic variables, out-of-bounds array access, and shift-by-width. Reference \
specific C/C++ standard clauses where possible.

3. **RAII & Resource Lifecycle:** In C++, verify that every resource acquisition \
has a corresponding release via RAII wrappers (`std::unique_ptr`, `std::lock_guard`). \
In C, trace every `fopen`/`malloc`/`pthread_mutex_lock` to its matching close/free/unlock. \
In Rust, verify `Drop` implementations are correct for FFI resources.

4. **Ownership & Borrowing (Rust):** Check `unsafe` blocks for soundness — \
does the raw pointer access respect the original borrow's lifetime? Flag \
`transmute`, `mem::forget`, and `ManuallyDrop` misuse. Verify that `Send`/`Sync` \
bounds are correct for concurrent types.

5. **Concurrency Bugs:** Identify data races, deadlocks (lock ordering violations), \
TOCTOU races on file system operations, and non-atomic access to shared state. \
Check for proper use of `std::atomic`, `std::mutex`, `pthread_mutex_t`, or \
Rust's `Arc<Mutex<T>>`.

For each finding, specify the exact memory/UB category, the trigger condition, \
and whether sanitisers (ASan, MSan, TSan, UBSan) would catch it.
"""

_LANG_SYSTEMS_DESIGN = """\
## Language Expert: Systems Programming — Code Design

Evaluate architecture and design in C, C++, Rust, and Objective-C codebases:

1. **Ownership Model Clarity:** Assess whether the code has a clear ownership \
model for every heap allocation. In C, are there documented conventions for who \
frees what? In C++, is the codebase using smart pointers consistently, or mixing \
raw and smart pointers? In Rust, evaluate whether `Rc`/`Arc` usage indicates \
a design that could use simpler ownership.

2. **Abstraction Layer Design:** Evaluate the use of virtual dispatch (C++ vtables, \
Rust trait objects) vs. static dispatch (templates, generics). Check for \
template bloat in C++, excessive trait object boxing in Rust. Assess whether \
C code uses function pointer tables (manual vtables) consistently.

3. **Error Handling Strategy:** In C, check for consistent `errno`/return-code \
patterns and whether callers always check return values. In C++, assess \
exception safety guarantees (basic, strong, nothrow). In Rust, evaluate \
`Result`/`Option` chaining and whether `unwrap()`/`expect()` appear in \
library code.

4. **ABI & FFI Boundaries:** Evaluate `extern "C"` interfaces for correctness — \
struct layout (`#[repr(C)]`, `__attribute__((packed))`), calling conventions, \
null pointer handling across FFI boundaries. Check for ABI compatibility across \
compilation units.

5. **Build & Compilation Units:** Assess header hygiene (include guards, forward \
declarations), translation unit boundaries, and link-time dependencies. In Rust, \
evaluate crate boundaries and feature flag design.

Provide a design assessment with concrete refactoring suggestions that respect \
systems-programming constraints (no hidden allocations, deterministic destruction, \
real-time compatibility).
"""

_LANG_SYSTEMS_FLOW = """\
## Language Expert: Systems Programming — Code Flow

Trace execution flow with focus on low-level control paths in C, C++, Rust, \
and Objective-C:

1. **Pointer & Reference Chains:** Trace pointer indirection through struct \
members, `void*` casts, and pointer arithmetic. Map which functions receive \
borrowed vs. owned pointers. Show where pointer provenance is lost through \
casts or arithmetic.

2. **Stack vs. Heap Flow:** Track object lifetime across function boundaries. \
Show where stack-allocated objects are returned by reference (dangling), where \
heap allocations are passed through layers, and where ownership transfers occur.

3. **Exception & Longjmp Paths:** In C++, map exception propagation through \
the call stack, including destructor invocations during stack unwinding. In C, \
trace `setjmp`/`longjmp` paths and identify resources that leak during non-local \
jumps. In Rust, map `panic!` propagation and `catch_unwind` boundaries.

4. **Preprocessor & Conditional Compilation:** Expand `#ifdef`/`#ifndef` paths \
to show which code actually compiles under each platform/configuration. Map \
feature-flag-conditional code paths in Rust (`#[cfg(feature = "...")]`).

5. **Interrupt & Signal Handling:** Identify signal handlers and their safety \
(only async-signal-safe functions allowed). Trace interrupt service routines \
in embedded code. Map `volatile` accesses that communicate with hardware or \
signal handlers.

Present the flow annotated with memory operations (alloc, move, copy, free) \
at each step to make the resource lifecycle visible.
"""

_LANG_SYSTEMS_MERMAID = """\
## Language Expert: Systems Programming — Mermaid Diagrams

Generate Mermaid diagrams for systems code (C, C++, Rust, Objective-C):

1. **Memory Ownership Diagrams:** Create diagrams showing ownership transfers \
between components — use directed edges for `move`, bidirectional for `borrow`, \
and dashed for `weak` references. Annotate lifetimes where applicable. Show \
`Rc`/`Arc`/`shared_ptr` reference count relationships.

2. **Struct & Union Layout:** Use class diagrams to show struct composition, \
including field sizes, alignment padding, and byte offsets. Show inheritance \
hierarchies with vtable pointers annotated.

3. **Concurrency Architecture:** Create sequence diagrams showing thread \
interactions, mutex acquisitions (with lock ordering), atomic operations, \
and channel message passing. Highlight potential deadlock cycles.

4. **State Machine Diagrams:** Many systems programs implement state machines \
explicitly (embedded, protocol parsers). Generate state diagrams from `switch` \
statements or `match` arms, showing all transitions and guard conditions.

5. **Build & Link Dependency Graph:** Show compilation unit dependencies, \
static vs. dynamic library links, and feature-flag-driven inclusion. Highlight \
circular dependencies.

Ensure all diagrams use Mermaid syntax. For memory diagrams, use node shapes \
and colours to distinguish stack (rectangle), heap (rounded), and static \
(hexagon) allocations.
"""

_LANG_SYSTEMS_REQUIREMENT = """\
## Language Expert: Systems Programming — Requirements Extraction

Extract requirements from systems code (C, C++, Rust, Objective-C):

1. **Memory & Performance Requirements:** Extract implicit performance \
constraints — stack size limits, heap budget, allocation-free hot paths, \
real-time deadlines. Identify functions annotated `noexcept`, `[[nodiscard]]`, \
or `#[must_use]` that encode correctness requirements.

2. **Platform & Hardware Requirements:** Identify target architecture \
assumptions — endianness (`htonl`/`ntohl`), word size (`sizeof(void*)`), \
alignment requirements, SIMD instruction sets. Extract OS-specific API usage \
(POSIX, Win32, embedded HAL).

3. **Safety & Security Requirements:** Extract requirements for memory safety \
guarantees, bounds checking, stack canaries, ASLR compatibility. Identify \
`unsafe` blocks in Rust and document what invariants they require callers \
to maintain.

4. **ABI & Compatibility Requirements:** Document struct layout requirements \
for FFI, serialisation format constraints, wire protocol versioning, and \
backward compatibility guarantees.

5. **Concurrency Requirements:** Extract threading model requirements — \
single-threaded sections, lock-free data structure invariants, \
interrupt-safe function requirements, `Send`/`Sync` bounds, and \
async runtime requirements.

Present each requirement with its source location, whether it is an explicit \
assertion or an implicit assumption, and the risk level if violated.
"""

_LANG_SYSTEMS_STATIC = """\
## Language Expert: Systems Programming — Static Analysis

Perform deep semantic static analysis for C, C++, Rust, and Objective-C:

1. **Lifetime & Borrow Analysis:** Manually trace object lifetimes through \
function calls. Identify where a pointer/reference outlives its referent. \
In Rust, check `unsafe` blocks for lifetime violations the borrow checker \
cannot see. In C/C++, flag stack-address escapes and use-after-scope.

2. **Integer & Arithmetic Safety:** Check for signed overflow (UB in C/C++), \
unsigned wrap-around, truncation on cast (`int` to `short`), division by zero, \
and shift UB (`shift >= width`). Verify correct use of `<stdint.h>` / \
`<cstdint>` fixed-width types.

3. **Null & Uninitialised Analysis:** Trace every pointer from allocation to \
dereference. Flag paths where a pointer may be null or uninitialised at the \
point of use. Check for partial struct initialisation (missing designated \
initialisers). In Rust, check `MaybeUninit` usage for correctness.

4. **Concurrency Safety Analysis:** Verify all shared mutable state is \
protected by synchronisation. Check lock ordering consistency across the \
codebase. Flag non-atomic reads of variables written by another thread. \
Verify `memory_order` arguments on atomic operations.

5. **Preprocessor & Type System Abuse:** Flag macros that evaluate arguments \
multiple times, type-unsafe `void*` casts without size validation, and C++ \
`reinterpret_cast` / C-style casts that bypass type safety.

For each finding, provide the CWE identifier where applicable and specify \
which compiler flags or sanitisers (-Wall -Wextra -fsanitize=...) would catch it.
"""

_LANG_SYSTEMS_COMMENT = """\
## Language Expert: Systems Programming — PR Review Comments

Write PR review comments for systems code (C, C++, Rust, Objective-C):

1. **Memory Safety Comments:** For every `malloc`/`new`/`Box::new`, comment \
on the ownership and deallocation plan. For raw pointer usage in Rust `unsafe` \
blocks, request documentation of safety invariants. Flag missing null checks \
after allocation.

2. **Undefined Behaviour Warnings:** Call out potential UB with specific \
standard references. Suggest compiler flags to catch the issue \
(`-fsanitize=undefined`, `-fstack-protector`). Recommend `static_assert` \
or `const_assert!` to enforce assumptions at compile time.

3. **Error Handling Comments:** If a system call return value goes unchecked, \
flag it. Suggest `[[nodiscard]]` or `#[must_use]` annotations. For C++ code, \
comment on exception safety guarantees of modified functions.

4. **Performance Comments:** Flag unnecessary copies (suggest `std::move`, \
`&&`, or borrowing). Comment on cache-unfriendly access patterns (struct-of-arrays \
vs. array-of-structs). Flag heap allocations in hot paths.

5. **Portability Comments:** Flag platform-specific assumptions (endianness, \
pointer size, struct packing). Suggest `static_assert(sizeof(...))` guards. \
Comment on non-standard compiler extensions.

Write comments referencing specific compiler warnings, sanitiser flags, and \
language standard sections where possible.
"""

_LANG_SYSTEMS_COMMIT = """\
## Language Expert: Systems Programming — Commit Analysis

Analyse commit history in systems codebases (C, C++, Rust, Objective-C):

1. **Memory Safety Evolution:** Track commits that introduced or removed \
`unsafe` blocks, changed ownership patterns (raw pointers to smart pointers), \
or added/removed manual memory management. Identify trends toward safer \
patterns over time.

2. **Compiler & Toolchain Changes:** Track changes to `CMakeLists.txt`, \
`Makefile`, `Cargo.toml`, warning flags, sanitiser configurations, and CI \
build matrix. Identify when new warnings were enabled and whether violations \
were fixed.

3. **ABI-Breaking Changes:** Identify commits that changed struct layouts, \
function signatures in public headers, or library version numbers. Flag \
missing version bumps when ABI breaks occurred.

4. **Security Patches:** Identify commits that fix CVEs or security bugs — \
buffer overflow fixes, bounds check additions, integer overflow guards. Assess \
whether the fix is complete or leaves related code vulnerable.

5. **Platform Support Changes:** Track addition or removal of platform-specific \
`#ifdef` blocks, new architecture support, and portability fixes. Identify \
commits that broke one platform while fixing another.

Present the analysis as a timeline of significant architectural decisions, \
focusing on memory safety, correctness, and platform evolution.
"""

# ===================================================================
# 3. JVM (Java, Kotlin, Scala, Groovy, Clojure)
# ===================================================================

_LANG_JVM_BUG = """\
## Language Expert: JVM — Bug Analysis

Focus your bug analysis on JVM-specific pitfalls (Java, Kotlin, Scala, Groovy):

1. **Thread Safety & Visibility:** Identify shared mutable state accessed \
without synchronisation. Check for `volatile` fields that need `AtomicReference` \
instead. Flag `HashMap` usage in concurrent contexts (should be \
`ConcurrentHashMap`). Check for double-checked locking without `volatile`. \
Look for `synchronized` blocks with inconsistent monitor objects.

2. **Null Safety & Optional Misuse:** In Java, trace `null` propagation through \
call chains. Flag `Optional.get()` without `isPresent()` check. In Kotlin, \
check for `!!` (bang-bang) operator abuse that defeats null safety. Look for \
platform types from Java interop leaking nulls into Kotlin code.

3. **Resource & Memory Leaks:** Identify `Closeable`/`AutoCloseable` resources \
not wrapped in try-with-resources. Check for `InputStream`, `Connection`, and \
`ResultSet` objects that escape their scope. Flag `static` collections that \
grow unbounded (memory leak). Check for classloader leaks in web applications.

4. **Serialisation Vulnerabilities:** Flag classes implementing `Serializable` \
without defining `serialVersionUID`. Identify deserialisation of untrusted \
data (`ObjectInputStream.readObject()`). Check for transient fields that \
should be excluded from serialisation.

5. **Stream API & Lambda Pitfalls:** Identify side-effect-ful operations in \
`Stream.map()` or `Stream.filter()`. Flag `parallel()` streams with non-thread-safe \
collectors. Check for `Stream` reuse (streams are single-use). Look for lambda \
captures of mutable local variables.

Present findings with the Java/Kotlin source line, the failure scenario, and \
references to Effective Java items or Kotlin best practices where applicable.
"""

_LANG_JVM_DESIGN = """\
## Language Expert: JVM — Code Design

Evaluate architecture and design patterns for JVM codebases (Java, Kotlin, \
Scala, Groovy):

1. **SOLID Adherence & Pattern Usage:** Assess Single Responsibility across \
classes. Check for Interface Segregation — are interfaces too fat? Evaluate \
Dependency Inversion — does the code depend on abstractions or concretions? \
Identify misused patterns: Singleton as global state, overuse of Factory for \
simple constructors, God Objects.

2. **Generics & Type System Leverage:** Evaluate use of bounded type parameters, \
wildcard capture (`? extends`, `? super`). In Kotlin, check reified type \
parameter usage, sealed class hierarchies for exhaustive `when`. In Scala, \
assess type class usage and implicit resolution complexity.

3. **Concurrency Architecture:** Evaluate thread pool sizing and configuration. \
Check for `ExecutorService` lifecycle management. Assess whether reactive \
patterns (Project Reactor, RxJava, Kotlin Coroutines) are used consistently \
or mixed with blocking code.

4. **Framework Integration:** Evaluate Spring dependency injection — circular \
beans, overuse of `@Autowired` field injection vs. constructor injection. \
Check for proper transaction boundary definition (`@Transactional` scope). \
Assess Hibernate/JPA entity design — lazy vs. eager loading, N+1 query risks.

5. **Build & Module Structure:** Evaluate Maven/Gradle module boundaries. \
Check for proper encapsulation between modules (`internal` in Kotlin, \
module-info.java in JPMS). Assess dependency management — version conflicts, \
unused dependencies, BOM usage.

Provide an architecture assessment with Effective Java / Kotlin best practices \
references and concrete refactoring suggestions.
"""

_LANG_JVM_FLOW = """\
## Language Expert: JVM — Code Flow

Trace execution flow with attention to JVM-specific dispatch and lifecycle:

1. **Dependency Injection Flow:** Trace the Spring/Guice/Dagger wiring — \
from `@Component` scanning through `@Autowired` injection to method invocation. \
Show the proxy chain for `@Transactional`, `@Cacheable`, `@Async` annotated \
methods where AOP wraps the original call.

2. **Exception Propagation & Checked Exceptions:** Map checked and unchecked \
exception flows through the call stack. Show where exceptions are caught, \
wrapped (`new RuntimeException(cause)`), or logged-and-swallowed. Identify \
`try` blocks whose `catch` clause handles too broad an exception type.

3. **Reactive & Coroutine Chains:** Trace Mono/Flux pipelines or Kotlin \
Flow/Channel chains step by step. Show where backpressure is applied, where \
`subscribeOn` vs. `publishOn` switches threads, and where blocking calls \
break the reactive chain.

4. **Classloader & Startup Flow:** Map the application startup sequence — \
static initialisers, `@PostConstruct`, `CommandLineRunner`, and bean \
lifecycle hooks. Show the order of module loading and where circular \
dependencies cause startup failures.

5. **Reflection & Dynamic Proxy Paths:** Trace `Method.invoke()`, \
`Proxy.newProxyInstance()`, and framework magic (Spring AOP, Hibernate \
lazy loading) that create invisible method calls not visible in the source.

Present the flow as a numbered sequence with annotations for thread context \
switches, proxy boundaries, and transaction scopes.
"""

_LANG_JVM_MERMAID = """\
## Language Expert: JVM — Mermaid Diagrams

Generate Mermaid diagrams for JVM-specific patterns:

1. **Class & Interface Hierarchies:** Create class diagrams showing \
interface implementations, abstract class hierarchies, and composition \
relationships. Annotate generics, sealed classes (Kotlin/Java 17+), and \
record types. Show Spring stereotype annotations on classes.

2. **Spring Bean Dependency Graph:** Show `@Component`, `@Service`, \
`@Repository` beans as nodes with injection edges. Highlight circular \
dependencies with red edges. Show `@Configuration` classes and their \
`@Bean` factory methods.

3. **Thread & Concurrency Diagrams:** Use sequence diagrams to show thread \
pool handoffs, `synchronized` block contention, `CompletableFuture` chains, \
and Kotlin coroutine scope hierarchies. Show where context switches occur.

4. **Transaction & Session Boundaries:** Show `@Transactional` scope boundaries \
in sequence diagrams. Illustrate Hibernate session lifecycle — where entities \
become detached, where lazy loading triggers additional queries (N+1).

5. **Deployment Architecture:** Generate deployment diagrams showing JVM \
instances, microservice communication patterns, and database connection \
pooling. Include JVM memory zones (heap, metaspace) where relevant.

Ensure diagrams use standard Mermaid syntax and keep node labels concise. \
Add notes for JVM-specific concepts (GC roots, classloader boundaries).
"""

_LANG_JVM_REQUIREMENT = """\
## Language Expert: JVM — Requirements Extraction

Extract requirements from JVM codebases:

1. **JVM Runtime Requirements:** Extract minimum Java/Kotlin/Scala version \
from `build.gradle`, `pom.xml`, and `sourceCompatibility`/`jvmTarget` settings. \
Identify JVM flags required for operation (`-Xmx`, `--add-opens`, \
`-XX:+UseG1GC`). Document garbage collector requirements.

2. **Framework & Library Requirements:** Map Spring Boot version, required \
starters, and auto-configuration dependencies. Extract database driver and \
connection pool requirements. Identify messaging system dependencies \
(Kafka, RabbitMQ, SQS).

3. **API Contract Requirements:** Extract REST API contracts from \
`@RequestMapping`, OpenAPI annotations, and Retrofit interfaces. Document \
request/response types, validation constraints (`@Valid`, `@NotNull`), and \
error response formats.

4. **Persistence Requirements:** Extract JPA entity relationships, database \
schema requirements (columns, indexes, constraints from annotations), and \
migration tool requirements (Flyway, Liquibase). Document transaction \
isolation level requirements.

5. **Security Requirements:** Extract authentication requirements from \
Spring Security configuration — roles, permissions, OAuth scopes. Document \
CORS policies, CSRF protection requirements, and API key management.

Present requirements grouped by layer (runtime, framework, API, persistence, \
security) with references to source annotations and configuration files.
"""

_LANG_JVM_STATIC = """\
## Language Expert: JVM — Static Analysis

Perform deep semantic static analysis for JVM languages:

1. **Null Safety Analysis:** Trace nullability through every method chain. \
Flag methods that return null without documenting it (`@Nullable`). In Kotlin, \
check platform type contamination from Java libraries. Verify `Optional` is \
not used as a method parameter or field type (Effective Java Item 55).

2. **Concurrency Correctness:** Verify that all mutable shared state is \
protected. Check for non-atomic compound operations (check-then-act). Verify \
`volatile` semantics are sufficient (single read/write) vs. needing `Atomic*` \
classes. Detect potential deadlocks from nested `synchronized` blocks.

3. **Resource Leak Analysis:** Trace every `AutoCloseable` from creation to \
close. Identify resources opened in constructors that leak if construction \
fails partway. Flag JDBC `Connection`, `Statement`, `ResultSet` chains where \
any step can leak if a subsequent allocation fails.

4. **Generics & Type Erasure Issues:** Identify `instanceof` checks against \
generic types that are erased at runtime. Flag `(List<String>)(List<?>)` \
unsafe casts. Check for raw type usage that defeats generic type safety.

5. **Performance Anti-Patterns:** Flag `String` concatenation in loops \
(use `StringBuilder`), autoboxing in hot paths, `LinkedList` usage where \
`ArrayList` suffices, and `synchronized` on `String` literals (interning \
causes unexpected sharing).

Present findings with references to SpotBugs/ErrorProne/SonarQube rule IDs \
and Effective Java item numbers where applicable.
"""

_LANG_JVM_COMMENT = """\
## Language Expert: JVM — PR Review Comments

Write PR review comments tailored for JVM codebases:

1. **Null & Optional Handling:** Comment on null-returning methods that lack \
`@Nullable` annotations. Suggest `Optional` for return types but flag it in \
parameters. For Kotlin code, flag `!!` usage and suggest safe alternatives \
(`?.let`, `?:`, `requireNotNull`).

2. **Concurrency Comments:** Flag unsynchronised access to mutable shared \
state. Suggest `ConcurrentHashMap` over `Collections.synchronizedMap`. Comment \
on `@Async` methods that return `void` (losing exception information). \
Recommend `CompletableFuture` or Kotlin `Deferred` instead.

3. **Resource Management Comments:** Insist on try-with-resources for all \
`AutoCloseable` resources. Flag `finally` blocks with cleanup code that should \
use try-with-resources. Comment on `@PreDestroy` lifecycle methods that may \
not run during forced shutdown.

4. **API Design Comments:** Suggest `sealed` interfaces for closed type \
hierarchies. Recommend `record` types (Java 16+) for immutable data carriers. \
Comment on method parameter counts (suggest builder or parameter object for \
4+ parameters). Flag `void` methods that should return `this` for fluent APIs.

5. **Testing Comments:** Suggest specific test cases for null inputs, empty \
collections, and boundary values. Recommend Mockito `verify()` for interaction \
tests. Flag `@SpringBootTest` where a lighter `@WebMvcTest` or `@DataJpaTest` \
would suffice.

Write comments referencing Effective Java items, Kotlin coding conventions, \
and SonarQube rules for justification.
"""

_LANG_JVM_COMMIT = """\
## Language Expert: JVM — Commit Analysis

Analyse commit history in JVM codebases:

1. **Java Version Migration:** Track commits that upgraded Java/Kotlin source \
compatibility levels. Identify adoption of new language features — records, \
sealed classes, pattern matching, text blocks, `var` type inference. Assess \
whether migration was complete or left legacy patterns.

2. **Framework Upgrades:** Track Spring Boot, Hibernate, and dependency \
version bumps. Identify breaking changes — removed deprecated APIs, changed \
auto-configuration behaviour, new required properties. Flag commits that \
bumped versions without updating affected code.

3. **Concurrency Pattern Changes:** Identify commits that changed threading \
models — from `synchronized` to `ReentrantLock`, from thread pools to reactive \
streams, from callbacks to coroutines. Assess whether the migration was atomic \
or left the codebase in a mixed state.

4. **Database Schema Migrations:** Track Flyway/Liquibase migration scripts. \
Identify schema changes that could cause downtime (column renames, type changes). \
Flag missing rollback scripts and incompatible migration ordering.

5. **Test Infrastructure Changes:** Track introduction of test frameworks, \
mocking libraries, and test containers. Identify commits that changed test \
strategy (unit to integration, mock to testcontainer). Flag deleted tests \
and assess coverage impact.

Provide a chronological analysis highlighting major architectural decisions, \
version migrations, and their downstream effects.
"""

# ===================================================================
# 4. DOTNET (C#, F#, Visual Basic)
# ===================================================================

_LANG_DOTNET_BUG = """\
## Language Expert: .NET — Bug Analysis

Focus your bug analysis on .NET-specific pitfalls (C#, F#, VB.NET):

1. **Async/Await Deadlocks & Misuse:** Identify `.Result` or `.Wait()` calls \
on `Task`/`ValueTask` that cause deadlocks in UI or ASP.NET contexts. Flag \
`async void` methods (should be `async Task` except for event handlers). Check \
for missing `ConfigureAwait(false)` in library code. Detect fire-and-forget \
tasks whose exceptions go unobserved.

2. **IDisposable Lifecycle Bugs:** Trace every `IDisposable` object from \
creation to disposal. Flag objects not wrapped in `using` statements or \
`using` declarations. Identify `IDisposable` fields in classes that don't \
implement `IDisposable` themselves. Check for disposal of injected dependencies \
that shouldn't be disposed by the consumer.

3. **Null Reference & Nullable Context:** Trace nullable reference flow through \
method chains. Flag suppression operators (`!`) that override nullable warnings. \
Identify APIs that return null despite non-nullable signatures. Check \
`#nullable enable` coverage — are there gaps in nullable contexts?

4. **LINQ Deferred Execution Bugs:** Identify LINQ queries that are enumerated \
multiple times (triggering repeated database queries or side effects). Flag \
`IQueryable` chains that pull entire tables into memory with premature \
`.ToList()` or that fail at runtime due to untranslatable expressions.

5. **Task vs. ValueTask Misuse:** Flag `ValueTask` being awaited multiple \
times or stored in variables for later use (both violations). Check for \
`Task.Run` in ASP.NET request handlers (wastes a thread pool thread). Identify \
`CancellationToken` parameters that are accepted but never checked.

Present findings with C# code references, the failure scenario, and links \
to the relevant .NET documentation or Roslyn analyser rules.
"""

_LANG_DOTNET_DESIGN = """\
## Language Expert: .NET — Code Design

Evaluate architecture and design in .NET codebases (C#, F#, VB.NET):

1. **Dependency Injection Architecture:** Assess `IServiceCollection` \
registration — are lifetimes correct (Transient vs. Scoped vs. Singleton)? \
Flag captive dependencies (Scoped injected into Singleton). Evaluate whether \
the DI container is used as a Service Locator anti-pattern.

2. **Async Architecture Consistency:** Assess whether the async boundary is \
clean — no mixing of blocking and async code. Check for sync-over-async \
wrapping and async-over-sync wrapping. Evaluate `Channel<T>` and \
`IAsyncEnumerable` usage for streaming scenarios.

3. **Entity Framework & Data Access:** Evaluate DbContext lifetime management. \
Check for proper query/command separation (CQRS patterns). Assess migration \
strategy and whether the data model leaks into the domain layer. Flag \
`Include()` chains that indicate missing projections.

4. **API Surface Design:** Evaluate controller design — are they thin? \
Check for proper model binding, validation (FluentValidation, DataAnnotations), \
and result types. Assess versioning strategy, content negotiation, and \
middleware pipeline ordering.

5. **Cross-Cutting Concerns:** Evaluate logging (structured logging with \
Serilog/ILogger), health checks, configuration binding \
(`IOptions<T>`/`IOptionsSnapshot<T>`), and feature flags. Check for consistent \
exception handling middleware.

Provide recommendations using .NET idioms — `record` types for DTOs, \
`sealed` classes, nullable reference types, and Source Generators where applicable.
"""

_LANG_DOTNET_FLOW = """\
## Language Expert: .NET — Code Flow

Trace execution flow with attention to .NET-specific patterns:

1. **ASP.NET Request Pipeline:** Trace a request from Kestrel through \
middleware pipeline (`UseRouting`, `UseAuthentication`, `UseAuthorization`) \
to the endpoint. Show model binding, validation, action filter execution \
order, and result formatting. Map exception handling middleware.

2. **Async State Machine Flow:** Trace `async`/`await` chains showing where \
the state machine captures `SynchronizationContext`. Show continuation \
scheduling — which thread resumes after each `await`? Identify points where \
`ConfigureAwait(false)` changes the continuation context.

3. **DI Container Resolution Flow:** Trace `IServiceProvider.GetService<T>` \
resolution through the dependency graph. Show constructor injection chains, \
factory delegate invocations, and decorator patterns. Map scope creation \
and disposal during request processing.

4. **Entity Framework Query Flow:** Trace a LINQ query from `IQueryable` \
construction through expression tree building, SQL translation, execution, \
and materialisation. Show where deferred execution triggers actual database \
calls and where change tracking attaches entities.

5. **Event & Messaging Flow:** Trace `IMediator.Send()` (MediatR), domain \
events, and message broker integration (MassTransit, NServiceBus). Show \
handler resolution, pipeline behaviour execution, and saga/process manager \
state transitions.

Present flows with clear annotations for thread transitions, context \
switches, and scope boundaries.
"""

_LANG_DOTNET_MERMAID = """\
## Language Expert: .NET — Mermaid Diagrams

Generate Mermaid diagrams for .NET-specific architectures:

1. **Clean Architecture Layers:** Create component diagrams showing Domain, \
Application, Infrastructure, and Presentation layers. Show dependency \
direction (inward only). Annotate interfaces at boundaries and their \
implementations.

2. **ASP.NET Middleware Pipeline:** Use a flowchart to show the middleware \
execution order — each middleware as a node with request/response paths. \
Highlight short-circuit points (e.g., `UseAuthorization` returning 401).

3. **Entity Framework Relationships:** Generate ER diagrams from entity \
classes showing navigation properties, foreign keys, owned types, and \
table-per-hierarchy inheritance mappings. Annotate with cascade delete rules.

4. **Async Flow Diagrams:** Use sequence diagrams to show async/await chains \
across service layers. Annotate thread pool thread vs. IO thread vs. UI thread \
at each await point. Show `CancellationToken` propagation.

5. **Message & Event Flow:** Create sequence diagrams for CQRS/event-driven \
patterns showing Command -> Handler -> Event -> Handler chains. Show message \
bus transport between microservices.

Use standard Mermaid syntax and keep diagrams focused — split complex \
architectures into multiple diagrams rather than one monolith.
"""

_LANG_DOTNET_REQUIREMENT = """\
## Language Expert: .NET — Requirements Extraction

Extract requirements from .NET codebases:

1. **.NET Runtime Requirements:** Extract target framework monikers \
(`net8.0`, `netstandard2.1`) from `.csproj` files. Identify runtime-specific \
APIs used (preview features, platform-specific TFMs). Document required \
workloads and SDK versions.

2. **NuGet Dependency Requirements:** Map package references, version ranges, \
and transitive dependencies. Identify packages with known vulnerabilities. \
Extract `<PackageReference>` constraints and central package management \
(`Directory.Packages.props`) policies.

3. **Configuration Requirements:** Extract `IConfiguration` bindings — \
`IOptions<T>` classes, `appsettings.json` schema, environment variable \
overrides. Document required vs. optional configuration sections and valid \
value ranges.

4. **Infrastructure Requirements:** Extract connection strings, message broker \
endpoints, cache providers, and health check dependencies. Document required \
external services from `Program.cs` / `Startup.cs` service registrations.

5. **Security Requirements:** Extract authentication schemes (`AddJwtBearer`, \
`AddOpenIdConnect`), authorization policies, CORS origins, and data protection \
key storage requirements. Document API key and certificate management needs.

Present requirements grouped by deployment concern (runtime, dependencies, \
config, infrastructure, security) with source file references.
"""

_LANG_DOTNET_STATIC = """\
## Language Expert: .NET — Static Analysis

Perform deep semantic static analysis for .NET (C#, F#, VB.NET):

1. **Nullable Reference Analysis:** Trace nullable flow through the entire \
call graph. Identify methods that return null despite non-nullable signatures. \
Flag `null!` suppressions and assess whether they are justified. Check that \
`[NotNullWhen]`, `[MaybeNullWhen]` attributes are correct.

2. **Async Correctness Analysis:** Verify every `async` method properly awaits \
all tasks. Flag `Task` objects that are returned but not awaited (fire-and-forget). \
Check for `async` lambdas passed to `void`-delegate parameters. Verify \
`ValueTask` is consumed exactly once.

3. **Disposal Correctness:** Trace `IDisposable` object lifetimes across \
method boundaries. Identify fields that are disposed in `Dispose()` but could \
be null. Check for `Dispose()` called on objects injected via DI (whose lifetime \
is managed by the container). Verify `Dispose(bool)` pattern in unsealed classes.

4. **LINQ Translation Safety:** Identify `IQueryable` expressions that will \
fail translation to SQL — custom method calls, non-translatable `string` \
operations, conditional logic that EF Core cannot convert. Flag client-side \
evaluation warnings.

5. **Performance Analysis:** Flag excessive boxing (value types cast to \
interfaces), unnecessary `ToList()` materialisation, string interpolation in \
hot paths (use `StringBuilder`), and `Regex` construction in loops \
(use `[GeneratedRegex]` or `Regex.CompileToAssembly`).

Present findings with Roslyn analyser rule IDs (CA*, IDE*) and severity \
recommendations for `.editorconfig`.
"""

_LANG_DOTNET_COMMENT = """\
## Language Expert: .NET — PR Review Comments

Write PR review comments for .NET codebases:

1. **Async Pattern Comments:** Flag `.Result`/`.Wait()` calls and suggest \
`await`. Comment on missing `CancellationToken` parameters in async methods. \
Suggest `ConfigureAwait(false)` for library code. Flag `async void` and \
suggest `async Task`.

2. **DI & Lifetime Comments:** Flag `new`-ing up services that should be \
injected. Comment on incorrect service lifetimes (Scoped in Singleton). \
Suggest `IOptions<T>` over injecting `IConfiguration` directly. Flag \
Service Locator usage (`IServiceProvider.GetService` outside composition root).

3. **Nullable Safety Comments:** Flag `!` null-forgiving operators and \
request justification. Suggest `?` propagation over explicit null checks. \
Comment on `#nullable disable` regions and encourage enabling nullable context.

4. **Modern C# Suggestions:** Suggest `record` types for immutable DTOs, \
`init`-only properties, file-scoped namespaces, pattern matching (`is`, \
`switch` expressions), `using` declarations over `using` statements, and \
primary constructors (C# 12).

5. **EF Core & Data Access Comments:** Flag missing `AsNoTracking()` for \
read-only queries. Comment on N+1 query risks in `Include()` chains. \
Suggest projections (`Select`) over loading full entities. Flag raw SQL \
without parameterisation.

Write comments referencing specific Roslyn analyser rules, .NET documentation \
pages, and established .NET patterns.
"""

_LANG_DOTNET_COMMIT = """\
## Language Expert: .NET — Commit Analysis

Analyse commit history in .NET codebases:

1. **Framework Migration Tracking:** Track `.csproj` target framework changes \
(`net6.0` -> `net8.0`). Identify adoption of new C# features across versions. \
Flag incomplete migrations where old patterns remain alongside new ones.

2. **NuGet Dependency Evolution:** Track package version changes in \
`Directory.Packages.props` or `.csproj` files. Identify major version bumps \
and their breaking change impact. Flag removed packages and their replacements.

3. **Architecture Pattern Changes:** Identify commits that introduced CQRS, \
MediatR, or changed from traditional N-tier to Clean Architecture. Track \
middleware pipeline changes and their ordering effects.

4. **EF Core Migration History:** Track database migration files. Identify \
schema changes that require data migration. Flag migrations that drop columns \
or change types without corresponding data transformation scripts.

5. **Configuration & Deployment Changes:** Track changes to `appsettings.json`, \
Docker files, CI/CD pipelines, and Azure/AWS deployment configurations. \
Identify security-sensitive changes (connection strings, authentication \
provider switches).

Present the analysis highlighting .NET version adoption, architectural \
maturity progression, and dependency management discipline.
"""

# ===================================================================
# 5. GO
# ===================================================================

_LANG_GO_BUG = """\
## Language Expert: Go — Bug Analysis

Focus your bug analysis on Go-specific idioms and pitfalls:

1. **Goroutine Leaks:** Trace every `go` statement to its termination. \
Identify goroutines that block forever on channel operations, context \
cancellation that never arrives, or `select` statements missing a `Done` \
case. Check for goroutines spawned in loops without back-pressure.

2. **Channel Deadlocks & Races:** Verify all channels are properly closed \
(only by senders, exactly once). Check for sends on closed channels (panic). \
Identify unbuffered channel operations that can deadlock when sender and \
receiver are on the same goroutine. Run a mental `go vet` / `go race` check.

3. **Error Handling Patterns:** Check every `if err != nil` block. Flag \
errors that are checked but not returned or wrapped (`fmt.Errorf("...: %w", err)`). \
Identify functions that ignore returned errors entirely (the `_` discard). \
Check for `errors.Is`/`errors.As` usage instead of type assertions on errors.

4. **Nil Interface & Pointer Bugs:** Identify nil pointer dereferences hidden \
behind interface values (a nil pointer stored in a non-nil interface). Check \
for methods called on nil receivers where the method accesses fields. Flag \
map access without nil-map checks.

5. **Defer Gotchas:** Check for `defer` in loops (resource accumulation). \
Identify defer with closures that capture loop variables (evaluating to the \
final value). Flag defer of `rows.Close()` before error check on `rows`. \
Check that named return values interact correctly with deferred functions.

Present bugs with Go Playground-reproducible examples where possible and \
suggest fixes using standard library patterns.
"""

_LANG_GO_DESIGN = """\
## Language Expert: Go — Code Design

Evaluate architecture and design using Go's philosophy of simplicity:

1. **Interface Design:** Assess interface size — Go idiom prefers small \
interfaces (1-3 methods). Flag interfaces defined before they are needed \
(accept interfaces, return structs). Check for interface pollution — too many \
interfaces that mirror struct APIs 1:1 instead of capturing behaviour.

2. **Package Structure & Dependency Direction:** Evaluate package boundaries. \
Check for circular imports (compile error in Go, but design issue if avoided \
through hacky restructuring). Assess whether the `internal/` package is used \
to prevent external access. Check for `cmd/` and `pkg/` layout conventions.

3. **Error Design:** Evaluate whether sentinel errors, custom error types, \
or error wrapping is used consistently. Check for proper error hierarchy using \
`errors.Is` and `errors.As`. Flag string-matching on error messages. Assess \
whether errors carry enough context for debugging.

4. **Concurrency Patterns:** Evaluate goroutine lifecycle management. Check \
for proper use of `context.Context` for cancellation propagation. Assess \
channel-based communication vs. shared-memory patterns. Evaluate worker pool \
implementations for correctness.

5. **Testing Strategy:** Assess test table patterns, test helper functions, \
and `testdata/` usage. Check for proper use of `t.Helper()`, `t.Parallel()`, \
and `testing.Short()`. Evaluate mock/stub approach — interfaces for \
dependency injection vs. concrete type testing.

Provide design feedback aligned with Go proverbs and Effective Go guidelines.
"""

_LANG_GO_FLOW = """\
## Language Expert: Go — Code Flow

Trace execution flow with Go-specific attention:

1. **Goroutine Lifecycle Flow:** Map every goroutine from spawn (`go func()`) \
to termination. Show channel communication between goroutines as message \
arrows. Trace `context.Context` propagation and cancellation cascading through \
the goroutine tree.

2. **Error Propagation Flow:** Trace errors from origin through every \
`if err != nil { return ..., err }` up the call stack. Show where errors \
are wrapped (`%w`), where they are transformed, and where they are logged \
and discarded. Identify error boundary layers.

3. **HTTP Handler Flow:** Trace a request from `http.ListenAndServe` through \
router (`mux`, `chi`, `gin`) to handler. Show middleware chain execution \
order, context value injection, and response writing. Map `defer` statements \
that execute during response.

4. **Defer Stack Unwinding:** Show the LIFO order of deferred function \
execution when a function returns. Trace how deferred functions interact with \
named return values. Show `defer`/`recover` patterns for panic handling.

5. **Interface Dispatch & Embedding:** Trace method calls through interface \
dispatch to concrete implementations. Show struct embedding composition and \
method promotion. Identify where promoted methods are shadowed.

Present flows with goroutine IDs annotated to make concurrent execution \
paths distinguishable.
"""

_LANG_GO_MERMAID = """\
## Language Expert: Go — Mermaid Diagrams

Generate Mermaid diagrams for Go-specific patterns:

1. **Goroutine Communication Diagram:** Create sequence diagrams showing \
goroutines as participants and channel operations (send/receive/close) as \
messages. Use activation bars to show when goroutines are blocked on channel \
operations. Include `select` branch visualization.

2. **Package Dependency Graph:** Generate a directed graph of package imports. \
Use subgraphs for `internal/`, `cmd/`, and `pkg/` boundaries. Highlight \
external dependencies separately. Show test-only dependencies with dashed edges.

3. **Interface Implementation Map:** Create class diagrams showing interfaces, \
their implementing structs, and embedded struct composition. Annotate methods \
promoted through embedding. Show unexported types with special styling.

4. **Error Flow Diagram:** Create flowcharts showing error propagation paths \
from origin to handling point. Annotate wrapping points (`fmt.Errorf("%w")`) \
and terminal handling (log, return to user, retry).

5. **HTTP Middleware Pipeline:** Show the middleware chain as a flowchart \
with request flowing down and response flowing up. Include context value \
injection points and authentication/authorization decision nodes.

Use standard Mermaid syntax with clear node labels matching Go package and \
type names.
"""

_LANG_GO_REQUIREMENT = """\
## Language Expert: Go — Requirements Extraction

Extract requirements from Go codebases:

1. **Go Version & Module Requirements:** Extract Go version from `go.mod` \
(`go 1.22`). Identify version-specific features used (`range over int`, \
`log/slog`, generic types). Map module dependencies and their minimum \
versions from `go.sum`.

2. **Runtime & Deployment Requirements:** Identify CGO dependencies that \
require C compilers. Extract build tags (`//go:build linux && amd64`) that \
constrain deployment platforms. Document `GOMAXPROCS` and memory limit \
assumptions.

3. **External Service Requirements:** Extract database drivers, message \
broker clients, and HTTP client dependencies. Map connection string patterns \
and expected endpoints. Document health check and readiness probe requirements.

4. **Concurrency Requirements:** Identify goroutine pool sizes, channel \
buffer capacities, and context timeout values. Document expected concurrent \
load patterns and back-pressure mechanisms.

5. **Configuration Requirements:** Extract flag definitions (`flag.String`), \
environment variable reads (`os.Getenv`), and config file parsers (Viper, \
envconfig). Document required vs. optional configuration with defaults.

Present requirements with `go.mod` references and identify any requirements \
that differ between build tags or deployment configurations.
"""

_LANG_GO_STATIC = """\
## Language Expert: Go — Static Analysis

Perform deep semantic static analysis for Go:

1. **Race Condition Analysis:** Identify all shared mutable state across \
goroutines. Verify mutex protection covers all access points (not just writes). \
Check for `sync.Map` vs. `map` + `sync.Mutex` appropriateness. Flag \
`sync.WaitGroup` misuse (Add after goroutine start, negative counter).

2. **Error Path Analysis:** Verify every error return is checked. Trace error \
wrapping chains to ensure `errors.Is` and `errors.As` will work correctly. \
Flag errors constructed with `fmt.Errorf` without `%w` (breaks unwrapping). \
Check for panics in library code (should return errors instead).

3. **Resource Leak Detection:** Trace `*os.File`, `*http.Response.Body`, \
`*sql.Rows`, and `net.Conn` from creation to `Close()`. Flag missing `defer \
Close()` patterns. Check that HTTP response bodies are fully drained before \
close (prevents connection reuse). Verify `context.CancelFunc` is always called.

4. **Nil Safety Analysis:** Trace pointer and interface values through all \
paths. Identify where a nil check is missing before dereference. Flag nil-map \
writes (panic). Check for typed-nil interface bugs where `(*T)(nil)` is \
assigned to an interface, making `if err != nil` always true.

5. **Goroutine Leak Analysis:** For every `go` statement, verify there is a \
guaranteed termination path (context cancellation, channel close, or timeout). \
Flag goroutines that listen on channels that may never be written to.

Present findings with `go vet` and `staticcheck` rule references (e.g., \
SA1019, SA4006) and suggested fixes.
"""

_LANG_GO_COMMENT = """\
## Language Expert: Go — PR Review Comments

Write PR review comments for Go code:

1. **Error Handling Comments:** Flag unchecked errors (even from `fmt.Println`). \
Suggest error wrapping with `fmt.Errorf("context: %w", err)`. Comment on \
sentinel error usage and suggest custom error types when appropriate. Flag \
`log.Fatal` in library code.

2. **Goroutine Safety Comments:** Flag goroutine spawns without lifecycle \
management. Suggest `errgroup.Group` for coordinated goroutine work. Comment \
on missing context propagation to goroutines. Flag shared variables accessed \
from goroutines without synchronisation.

3. **Idiomatic Go Comments:** Suggest receiver name consistency (single letter, \
not `this`/`self`). Flag unnecessary interfaces — suggest accepting concrete \
types until an interface is needed. Comment on exported types that should be \
unexported. Suggest table-driven tests.

4. **Performance Comments:** Flag allocations in hot loops (`append` without \
pre-allocation, string concatenation). Suggest `strings.Builder` for \
concatenation, `sync.Pool` for frequent allocations. Comment on `reflect` \
usage that could use generics or code generation.

5. **API Design Comments:** Suggest functional options pattern for complex \
constructors. Flag exported functions returning unexported types. Comment on \
`context.Context` parameter placement (always first). Suggest `io.Reader` / \
`io.Writer` over concrete types for flexibility.

Write comments referencing Go proverbs, Effective Go, and `staticcheck` rules.
"""

_LANG_GO_COMMIT = """\
## Language Expert: Go — Commit Analysis

Analyse commit history in Go codebases:

1. **Go Version & Generics Adoption:** Track `go.mod` version changes. \
Identify commits that adopted generics, `slog`, `errors.Join`, or other \
version-specific features. Assess whether generic adoption replaced \
code-generation or interface-based patterns.

2. **Dependency Management:** Track `go.mod` dependency additions and \
removals. Identify dependency upgrades that required code changes. Flag \
commits that vendor dependencies vs. use module proxy. Track `replace` \
directive changes.

3. **Concurrency Pattern Evolution:** Identify commits that changed from \
`sync.Mutex` to channels or vice versa. Track introduction of \
`errgroup.Group`, `context.Context`, and structured concurrency patterns. \
Flag commits that spawned goroutines without corresponding lifecycle management.

4. **Error Handling Improvements:** Track migration from `errors.New` to \
wrapped errors (`%w`), from string matching to `errors.Is`/`errors.As`, and \
from panics to error returns. Identify commits that introduced custom error \
types.

5. **API Surface Changes:** Track exported type and function changes. Identify \
breaking changes to public APIs. Flag removed functions, changed signatures, \
and type renames that affect consumers.

Present analysis with `go.mod` version timeline and highlight commits that \
represent significant architectural shifts.
"""

# ===================================================================
# 6. FRONTEND (JavaScript, TypeScript, HTML, CSS, Dart)
# ===================================================================

_LANG_FRONTEND_BUG = """\
## Language Expert: Frontend — Bug Analysis

Focus your bug analysis on frontend-specific pitfalls (JS, TS, HTML, CSS, Dart):

1. **XSS & Injection Vulnerabilities:** Identify `innerHTML`, `dangerouslySetInnerHTML`, \
`document.write`, `eval`, and template literal injection points. Check for \
unsanitised user input reaching DOM manipulation or URL construction. Flag \
`postMessage` handlers without origin verification.

2. **Prototype Pollution & Type Coercion:** Flag `Object.assign` and spread \
operators on user-controlled input. Check for `__proto__` injection paths. \
Identify loose equality (`==`) comparisons that produce unexpected results. \
Flag `JSON.parse` of untrusted data without schema validation.

3. **Closure & Memory Leaks:** Identify closures that capture large scopes \
unnecessarily. Check for event listeners not removed on component unmount \
(React `useEffect` missing cleanup). Flag `setInterval`/`setTimeout` without \
clearance. Identify detached DOM node references.

4. **Event Loop Blocking:** Flag synchronous operations that block the main \
thread — large array sorts, synchronous XHR, `fs.readFileSync` in Electron. \
Identify `await` in loops that should use `Promise.all` or `Promise.allSettled`.

5. **State Management Bugs:** Identify React state mutations (direct array/object \
mutation instead of spreading). Check for stale closures in `useEffect`/`useCallback` \
with incorrect dependency arrays. Flag Redux selector recomputations and \
Zustand/Jotai subscription leaks.

Present findings with browser dev-tools reproduction steps and links to \
MDN/React documentation for proper patterns.
"""

_LANG_FRONTEND_DESIGN = """\
## Language Expert: Frontend — Code Design

Evaluate frontend architecture and design patterns:

1. **Component Architecture:** Assess component granularity — are components \
too large (god components) or over-decomposed? Evaluate prop drilling vs. \
context vs. state management. Check for proper separation of container \
(logic) and presentational (UI) components.

2. **Type Safety (TypeScript):** Evaluate TypeScript strictness settings \
(`strict`, `noUncheckedIndexedAccess`). Check for `any` type proliferation. \
Assess discriminated union usage for state modelling. Flag `as` type assertions \
that bypass safety.

3. **Bundle & Performance Architecture:** Evaluate code splitting strategy \
(route-based, component-based). Check for barrel file re-exports that defeat \
tree shaking. Assess lazy loading patterns (`React.lazy`, dynamic `import()`). \
Flag large dependencies imported for small utilities.

4. **CSS Architecture:** Evaluate styling approach consistency — CSS modules, \
Tailwind, styled-components, or CSS-in-JS. Check for specificity wars, \
`!important` overuse, and global style leaks. Assess responsive design \
breakpoint strategy.

5. **API Integration Layer:** Evaluate data fetching patterns — React Query, \
SWR, or manual `useEffect`+`fetch`. Check for proper loading/error/empty \
states. Assess caching strategy and optimistic update patterns.

Provide recommendations aligned with the framework's ecosystem best practices \
(React, Vue, Angular, Svelte conventions).
"""

_LANG_FRONTEND_FLOW = """\
## Language Expert: Frontend — Code Flow

Trace execution flow in frontend applications:

1. **Component Render Cycle:** Trace the React/Vue/Svelte render lifecycle — \
from state change to virtual DOM diff to actual DOM update. Show where \
`useMemo`/`useCallback`/`React.memo` prevent re-renders. Identify cascading \
re-renders from context or prop changes.

2. **Event Propagation:** Trace user events from DOM capture phase through \
bubble phase to handler execution. Show `preventDefault()`, `stopPropagation()` \
effects. Map synthetic event pooling in React. Identify event delegation \
patterns.

3. **Data Fetching Flow:** Trace data from API call through state management \
(Redux dispatch -> reducer -> selector -> component) or React Query cache. \
Show loading/error state transitions. Map optimistic update and rollback flows.

4. **SSR/SSG Hydration Flow:** Trace server-side rendering from data fetching \
through HTML generation to client-side hydration. Identify hydration mismatches \
(server HTML vs. client render). Show where `useEffect` runs only on client.

5. **Routing & Code Splitting:** Trace navigation from URL change through \
router matching to component loading. Show lazy-loaded chunk fetching, \
suspense boundary activation, and route guard evaluation.

Present flows with clear annotations for synchronous vs. asynchronous phases \
and main-thread vs. web-worker execution.
"""

_LANG_FRONTEND_MERMAID = """\
## Language Expert: Frontend — Mermaid Diagrams

Generate Mermaid diagrams for frontend-specific patterns:

1. **Component Tree & Data Flow:** Create tree diagrams showing component \
hierarchy with props flowing down and events/callbacks flowing up. Annotate \
context providers and consumers. Show state management store connections.

2. **State Machine Diagrams:** Model complex UI states (form wizard, \
authentication flow, modal lifecycle) as state machines. Show transitions \
triggered by user actions and API responses. Use XState conventions if applicable.

3. **Event Flow Diagrams:** Use sequence diagrams to show user interaction \
from click through event handler, state update, re-render, and DOM update. \
Include API calls and their async resolution.

4. **Build Pipeline Diagram:** Show the build process — source -> TypeScript \
compilation -> bundling -> tree shaking -> chunk splitting -> output. Annotate \
where optimizations occur.

5. **API Integration Sequence:** Create sequence diagrams showing client-server \
communication patterns — authentication token flow, request/response cycles, \
WebSocket connections, and error retry strategies.

Ensure diagrams are legible and use standard Mermaid syntax. Split complex \
UIs into focused diagrams per feature.
"""

_LANG_FRONTEND_REQUIREMENT = """\
## Language Expert: Frontend — Requirements Extraction

Extract requirements from frontend codebases:

1. **Browser & Runtime Requirements:** Extract target browsers from \
`browserslist` config, `tsconfig.json` target, and polyfill usage. Identify \
APIs used that require specific browser versions (Intersection Observer, \
Web Animations API, `structuredClone`). Document Node.js version for build tools.

2. **Framework & Library Requirements:** Map `package.json` dependencies. \
Identify peer dependency requirements and version constraints. Extract \
React/Vue/Angular version requirements and framework-specific plugins.

3. **API Contract Requirements:** Extract API endpoint URLs, request/response \
types (from TypeScript interfaces), authentication headers, and error \
response handling. Document expected API versions and feature flags.

4. **Accessibility Requirements:** Identify ARIA attributes, keyboard \
navigation handlers, screen reader text, focus management, and colour \
contrast requirements implied by the implementation.

5. **Performance Requirements:** Extract performance budgets from build \
configs, lazy loading boundaries, image optimization settings, and caching \
strategies. Document Core Web Vitals targets implied by optimization choices.

Present requirements grouped by runtime, dependencies, API, accessibility, \
and performance with source file references.
"""

_LANG_FRONTEND_STATIC = """\
## Language Expert: Frontend — Static Analysis

Perform deep semantic static analysis for frontend code:

1. **Type Safety Analysis (TypeScript):** Trace type narrowing through \
control flow. Identify `any` types that weaken the type system. Check generic \
constraints for correctness. Flag type assertions (`as`) that could fail at \
runtime. Verify discriminated union exhaustiveness in `switch` statements.

2. **Security Analysis:** Trace user input from form fields, URL parameters, \
and `postMessage` events to DOM sinks (`innerHTML`, `href`, `src`). Identify \
stored XSS vectors, open redirect vulnerabilities, and CSRF exposure. Check \
CSP compliance of inline scripts and styles.

3. **React Hook Analysis:** Verify `useEffect` dependency arrays are complete \
and correct. Flag stale closure bugs. Check for hooks called conditionally \
(violating Rules of Hooks). Identify `useMemo`/`useCallback` with unstable \
dependencies that defeat memoization.

4. **Bundle Size Analysis:** Identify heavy imports that could be replaced \
(`moment` -> `date-fns`, `lodash` -> native). Flag barrel imports that import \
entire libraries. Check for duplicate dependencies in the bundle. Identify \
CSS-in-JS runtime overhead.

5. **Accessibility Analysis:** Check for missing `alt` attributes, unlabelled \
form controls, missing heading hierarchy, insufficient color contrast in \
hardcoded styles, and missing keyboard event handlers alongside click handlers.

Present findings with ESLint rule references (eslint-plugin-react-hooks, \
@typescript-eslint, jsx-a11y) and severity levels.
"""

_LANG_FRONTEND_COMMENT = """\
## Language Expert: Frontend — PR Review Comments

Write PR review comments for frontend code:

1. **Security Comments:** Flag `dangerouslySetInnerHTML` and suggest DOMPurify. \
Comment on `eval` usage and suggest alternatives. Flag URL construction from \
user input without sanitisation. Recommend CSP headers.

2. **Performance Comments:** Flag unnecessary re-renders from inline object/array \
creation in JSX props. Suggest `React.memo` or `useMemo` for expensive \
computations. Comment on missing `key` props or index-as-key anti-pattern. \
Flag synchronous operations that should be deferred.

3. **TypeScript Comments:** Flag `any` types and suggest proper types. Comment \
on missing return type annotations for complex functions. Suggest `satisfies` \
operator (TS 4.9+) for type checking without widening. Recommend `unknown` \
over `any` for external data.

4. **Accessibility Comments:** Flag missing ARIA attributes, non-semantic HTML \
(`div` as button), missing focus management, and colour-only state indicators. \
Suggest semantic alternatives and keyboard navigation.

5. **Testing Comments:** Suggest Testing Library queries over implementation \
details (`getByRole` over `getByTestId`). Flag snapshot tests that test too \
much. Recommend user-interaction-centric tests. Suggest MSW for API mocking.

Write comments with links to MDN, React docs, and eslint rule names for \
justification.
"""

_LANG_FRONTEND_COMMIT = """\
## Language Expert: Frontend — Commit Analysis

Analyse commit history in frontend codebases:

1. **Framework & Tooling Migration:** Track React class-to-hooks migration, \
Vue Options-to-Composition API, Angular module-to-standalone. Identify bundler \
changes (Webpack -> Vite, CRA -> Next.js). Assess migration completeness.

2. **Dependency Churn:** Analyse `package-lock.json` / `yarn.lock` changes. \
Track major version bumps and breaking changes. Identify abandoned dependencies \
replaced by alternatives. Flag security advisory-driven updates.

3. **TypeScript Adoption:** Track `tsconfig.json` strictness progression. \
Identify `.js` -> `.ts` file renames. Monitor `any` type introduction vs. \
removal over time. Track type coverage trends.

4. **Performance Optimizations:** Identify commits that added code splitting, \
lazy loading, image optimization, or caching. Track bundle size changes \
across commits. Identify commits that regressed performance.

5. **Design System Evolution:** Track component library changes, theme updates, \
CSS methodology shifts, and responsive design additions. Identify commits \
that introduced accessibility improvements.

Present analysis as a frontend-specific evolution narrative covering framework \
maturity, type safety progression, and bundle health.
"""

# ===================================================================
# 7. FUNCTIONAL (Haskell, Elixir, Erlang, F#, Clojure)
# ===================================================================

_LANG_FUNCTIONAL_BUG = """\
## Language Expert: Functional Programming — Bug Analysis

Focus your bug analysis on functional-language-specific pitfalls (Haskell, \
Elixir, Erlang, Clojure, F#):

1. **Pattern Match Completeness:** Verify all `case`/`match`/`with` \
expressions handle every possible constructor. Flag `-Wincomplete-patterns` \
scenarios in Haskell. In Elixir, check for missing clauses in `case`, `cond`, \
and function heads. In Clojure, check `cond` without a default `:else`.

2. **Lazy Evaluation Pitfalls (Haskell):** Identify space leaks from \
unevaluated thunks accumulating in memory. Check for `foldl` usage that \
should be `foldl'` (strict). Flag lazy I/O (`hGetContents`) that causes \
resource leaks. Identify where `seq` or `BangPatterns` are needed.

3. **Process & Supervision Bugs (Elixir/Erlang):** Check for GenServer calls \
that can timeout and crash the caller. Verify supervision tree structure — are \
children properly supervised? Flag `Task.async` without `Task.await` (leaked \
processes). Check for message queue buildup in GenServers.

4. **Immutability Violations:** Identify use of mutable state — Haskell \
`IORef`/`MVar` without proper locking, Elixir ETS tables with race-prone \
access patterns, Clojure `atom` swap retries in side-effectful functions.

5. **Effect System & Monad Misuse:** Flag `unsafePerformIO` usage. Check for \
`IO` leaking into pure functions. In Elixir, identify side effects in functions \
whose names suggest purity. In Clojure, flag non-idempotent operations inside \
`swap!`.

Present findings with the specific language runtime implications and suggest \
idiomatic fixes using the language's standard library.
"""

_LANG_FUNCTIONAL_DESIGN = """\
## Language Expert: Functional Programming — Code Design

Evaluate architecture and design in functional codebases:

1. **Type Design & Algebraic Data Types:** Assess whether the type system is \
leveraged effectively — are sum types used to make illegal states \
unrepresentable? Check for boolean blindness (passing `Bool` where a custom \
type would be clearer). Evaluate phantom types and newtypes for domain modelling.

2. **Module & Namespace Organisation:** Evaluate module exports — are \
implementation details hidden? Check for module dependency cycles. In Haskell, \
assess `Internal` module conventions. In Elixir, evaluate context/boundary \
module design (Phoenix contexts).

3. **Effect Management:** Assess how side effects are managed — monad \
transformers (Haskell), `with` (Elixir), protocols (Clojure). Evaluate \
whether the pure/impure boundary is clear. Check for IO actions buried \
deep in otherwise pure computation chains.

4. **Concurrency Architecture:** In Elixir/Erlang, evaluate OTP supervision \
trees, GenServer design, and process communication patterns. In Haskell, \
assess STM usage, `async` library patterns. In Clojure, evaluate \
core.async channel architecture.

5. **Error Handling Philosophy:** Evaluate whether the codebase uses \
`Either`/`Result` types (Haskell, F#), tagged tuples `{:ok, _}/{:error, _}` \
(Elixir), or exception-based approaches consistently. Check for mixed error \
handling strategies that complicate composition.

Provide recommendations using functional programming principles — \
composition over inheritance, referential transparency, and principled \
type design.
"""

_LANG_FUNCTIONAL_FLOW = """\
## Language Expert: Functional Programming — Code Flow

Trace execution flow in functional codebases:

1. **Function Composition Chains:** Trace data transformation pipelines — \
Elixir `|>` pipes, Haskell `.` composition, Clojure `->>/->` threading. \
Show the type transformation at each step. Identify where the pipeline \
branches or fails.

2. **Pattern Match Dispatch:** Map function clause selection based on \
argument patterns. Show how multi-clause functions dispatch to different \
implementations. Trace guard conditions and their evaluation order.

3. **Recursion & Tail Call Optimisation:** Trace recursive function execution. \
Identify whether recursion is tail-recursive (eligible for TCO). In Haskell, \
trace `foldr` vs. `foldl'` evaluation order. In Elixir, trace `Enum.reduce` \
vs. manual recursion.

4. **Process Message Flow (Elixir/Erlang):** Trace messages between processes \
using sequence diagrams. Show GenServer `call`/`cast` routing, `handle_info` \
for system messages, and supervision tree restart flows after crashes.

5. **Monad/Effect Sequencing (Haskell):** Trace `do`-notation desugaring to \
`>>=` chains. Show where `IO` actions are sequenced, where `Maybe`/`Either` \
short-circuits, and where monad transformer stacks compose effects.

Present flows annotated with types at each step to make the transformation \
pipeline visible.
"""

_LANG_FUNCTIONAL_MERMAID = """\
## Language Expert: Functional Programming — Mermaid Diagrams

Generate Mermaid diagrams for functional programming patterns:

1. **Data Transformation Pipeline:** Create flowcharts showing data flowing \
through function composition chains. Annotate each transformation node with \
the function name and type signature. Show where pipelines branch or merge.

2. **Supervision Tree (Elixir/Erlang):** Create tree diagrams showing OTP \
supervision hierarchies. Annotate supervisor strategies (one_for_one, \
one_for_all, rest_for_one). Show dynamic supervisors and their children.

3. **Type Hierarchy / ADT Diagram:** Create diagrams showing algebraic data \
types — sum types as branching nodes, product types as records. Show type \
class instances (Haskell) or protocol implementations (Elixir).

4. **Process Communication (Elixir/Erlang):** Use sequence diagrams to show \
message passing between named processes, GenServers, and supervisors. Include \
timeout handling and crash/restart sequences.

5. **Monad Transformer Stack (Haskell):** Create layer diagrams showing monad \
transformer composition — `ReaderT Config (StateT AppState (ExceptT AppError IO))` \
as stacked layers with lift/unlift annotations.

Ensure diagrams focus on the data flow and type transformations that are central \
to functional architecture, not class hierarchies.
"""

_LANG_FUNCTIONAL_REQUIREMENT = """\
## Language Expert: Functional Programming — Requirements Extraction

Extract requirements from functional codebases:

1. **Runtime & Compiler Requirements:** Extract GHC/BEAM/JVM version \
requirements. Identify language extensions (`{-# LANGUAGE ... #-}` in Haskell), \
Elixir/Erlang OTP version requirements, and Clojure JVM compatibility. \
Document compiler flags and build tool configurations.

2. **Type System Requirements:** Extract type constraints, type class instances, \
and protocol implementations that encode business rules. Document phantom type \
invariants and smart constructor requirements. In Elixir, extract `@type` \
and `@spec` annotations.

3. **Concurrency Requirements (BEAM):** Extract process pool sizes, GenServer \
timeout values, supervision restart intensity/period settings. Document \
expected message rates and backpressure mechanisms. Identify ETS table \
configuration requirements.

4. **External Integration Requirements:** Extract database adapter \
configurations (Ecto repos, Persistent backends), HTTP client requirements, \
and message broker connections. Document expected external service APIs.

5. **Property-Based Testing Requirements:** Extract property definitions from \
QuickCheck/PropEr/StreamData tests that encode invariants. These properties \
often document requirements more precisely than prose specifications.

Present requirements with type signatures where applicable, as they serve \
as machine-checkable documentation in functional languages.
"""

_LANG_FUNCTIONAL_STATIC = """\
## Language Expert: Functional Programming — Static Analysis

Perform deep semantic static analysis for functional languages:

1. **Totality Analysis:** Verify all pattern matches are total (cover every \
constructor). In Haskell, check for partial functions (`head`, `tail`, `!!`, \
`fromJust`). In Elixir, check for `hd/1` on possibly-empty lists. Verify \
`case` expressions handle all tagged tuple variants.

2. **Purity Analysis:** Identify functions that perform side effects despite \
lacking effect markers. In Haskell, check for `unsafePerformIO` or `IORef` \
in supposedly pure code. In Elixir, identify functions without `!` suffix \
that raise exceptions or perform IO.

3. **Space Leak Detection (Haskell):** Identify thunk accumulation in \
recursive functions. Check `foldl` vs. `foldl'`, lazy `Map.fromList` building, \
and `Data.Text.Lazy` vs. strict text in concatenation loops. Flag lazy field \
bindings in data types that should be strict.

4. **Process Safety (Elixir/Erlang):** Verify GenServer state transitions are \
safe — no unbounded state growth, proper handle_call return values, timeout \
handling. Check for processes that accumulate messages faster than they process.

5. **Type Class Coherence (Haskell):** Verify orphan instances are avoided. \
Check that type class laws are respected (Functor, Monad, Eq laws). Identify \
overlapping instances that cause ambiguity. In Elixir, verify protocol \
implementations are consistent.

Present findings with GHC warning flags, Dialyzer/Credo rules, or HLint \
suggestions that would catch each issue.
"""

_LANG_FUNCTIONAL_COMMENT = """\
## Language Expert: Functional Programming — PR Review Comments

Write PR review comments for functional codebases:

1. **Totality & Safety Comments:** Flag partial functions and suggest total \
alternatives (`headMay`, `Enum.at/2` with default). Comment on incomplete \
pattern matches. Suggest `NonEmpty` list types where empty lists are invalid.

2. **Type Design Comments:** Suggest more precise types — newtypes over raw \
`String`/`Int`, sum types over booleans, phantom types for state tracking. \
Comment on type alias overuse where newtypes would provide safety.

3. **Effect Management Comments:** Flag IO in pure functions. Suggest moving \
side effects to the boundary. Comment on monad transformer stack complexity \
and suggest effect library alternatives. In Elixir, suggest moving side \
effects out of pure pipeline stages.

4. **Performance Comments:** Flag lazy thunk accumulation in Haskell. Suggest \
strict fields (`!`) in data types. Comment on `Enum` vs. `Stream` choice in \
Elixir. Flag unnecessary list materialisation in lazy languages.

5. **OTP/Concurrency Comments (Elixir):** Comment on GenServer design — \
suggest `call` vs. `cast` appropriateness. Flag missing supervision. Suggest \
`Task.Supervisor` over bare `Task.async`. Comment on ETS table access patterns.

Write comments with references to language community style guides, HLint \
rules, and Credo checks.
"""

_LANG_FUNCTIONAL_COMMIT = """\
## Language Expert: Functional Programming — Commit Analysis

Analyse commit history in functional codebases:

1. **Type System Evolution:** Track type signature additions, type class \
derivations, and ADT refactoring. Identify commits that introduced phantom \
types, GADTs, or type-level programming. In Elixir, track `@spec` and \
`@type` adoption.

2. **Effect Management Changes:** Track migration between effect systems — \
mtl to effect libraries, bare IO to tagless final. In Elixir, track \
introduction of Broadway, GenStage, or other effect management patterns.

3. **OTP Architecture Changes (BEAM):** Track supervision tree restructuring, \
GenServer additions/removals, and process communication pattern changes. \
Identify commits that fixed process leaks or message queue overflows.

4. **Dependency & Build Changes:** Track `stack.yaml`/`cabal` or `mix.exs` \
dependency evolution. Identify Hackage/Hex package additions and their \
justification. Flag deprecated packages that should be replaced.

5. **Property Test Coverage:** Track introduction of property-based tests. \
Identify properties that encode important invariants. Flag commits that \
removed properties or weakened test coverage.

Present analysis highlighting how the type system and functional patterns \
evolved to encode more invariants over time.
"""

# ===================================================================
# 8. INFRASTRUCTURE (Shell, SQL, Terraform, YAML, PowerShell)
# ===================================================================

_LANG_INFRA_BUG = """\
## Language Expert: Infrastructure — Bug Analysis

Focus your bug analysis on infrastructure code pitfalls (Shell, SQL, Terraform, \
YAML, PowerShell, Makefiles):

1. **Shell Injection & Command Safety:** Identify unquoted variable expansions \
that enable word splitting and glob expansion (`$var` vs. `"$var"`). Flag \
user input reaching `eval`, backtick execution, or `$()` without sanitisation. \
Check for command injection via filenames with spaces, newlines, or glob characters.

2. **SQL Injection & Query Safety:** Identify string concatenation used to \
build SQL queries. Flag missing parameterised queries / prepared statements. \
Check for `EXECUTE IMMEDIATE` with user input. Verify ORM-generated queries \
are parameterised.

3. **YAML Parsing Traps:** Flag Norway problem (`NO` interpreted as boolean \
`false`). Identify unquoted strings that YAML interprets as numbers, booleans, \
or null. Check for unsafe YAML loaders (`yaml.load` without `SafeLoader`, \
`YAML.load` in Ruby). Flag anchor/alias abuse.

4. **Idempotency Violations:** Check that shell scripts and Terraform \
configurations are safe to re-run. Flag `CREATE TABLE` without `IF NOT EXISTS`, \
file operations that fail if target exists, and Terraform resources that \
trigger replacement on re-apply.

5. **Secret Management:** Identify hardcoded passwords, API keys, and tokens \
in config files, environment variable defaults, and Terraform state. Flag \
secrets in shell history (`-p password` on command line). Check for `.env` \
files committed to version control.

Present findings with the CWE identifier and concrete exploitation scenario \
for each vulnerability.
"""

_LANG_INFRA_DESIGN = """\
## Language Expert: Infrastructure — Code Design

Evaluate architecture and design of infrastructure code:

1. **Shell Script Structure:** Assess `set -euo pipefail` usage for safety. \
Evaluate function decomposition — are scripts monolithic or modular? Check \
for proper signal handling (`trap`), temporary file cleanup, and exit code \
conventions. Assess whether complex scripts should be rewritten in Python.

2. **Terraform Module Design:** Evaluate module boundaries and composition. \
Check for hardcoded values that should be variables. Assess state management \
strategy (remote state, state locking). Evaluate provider version pinning \
and module source versioning.

3. **SQL Schema Design:** Evaluate normalisation level, index strategy, and \
constraint completeness (foreign keys, CHECK, NOT NULL). Assess migration \
strategy — are changes backward-compatible? Check for missing indexes on \
frequently queried columns.

4. **CI/CD Pipeline Design:** Evaluate pipeline stage organisation, caching \
strategy, and parallelism. Check for hardcoded secrets (should use vault/secrets \
manager). Assess deployment strategy (blue-green, canary, rolling).

5. **Configuration Management:** Evaluate separation of configuration from \
code. Check for environment-specific configs that should use templates. \
Assess secret rotation strategy and configuration drift detection.

Provide recommendations using infrastructure-as-code best practices, \
GitOps principles, and twelve-factor app methodology.
"""

_LANG_INFRA_FLOW = """\
## Language Expert: Infrastructure — Code Flow

Trace execution flow in infrastructure code:

1. **Shell Script Execution Flow:** Trace script execution from shebang through \
variable assignments, function definitions, and command pipelines. Show control \
flow through conditionals, loops, and `trap` handlers. Map subshell creation \
and variable scope isolation.

2. **Terraform Apply Flow:** Trace a `terraform apply` from variable resolution \
through resource dependency graph traversal. Show which resources are created, \
modified, or destroyed in what order. Map module composition and data source \
resolution.

3. **CI/CD Pipeline Flow:** Trace a pipeline from trigger (push, PR, schedule) \
through stages (build, test, deploy). Show conditional stage execution, \
artifact passing between stages, and approval gates.

4. **SQL Query Execution Flow:** Trace query execution from client submission \
through parsing, planning (show expected query plan), and execution. For \
stored procedures, trace control flow through cursors, loops, and exception \
handlers.

5. **Configuration Resolution Flow:** Trace how configuration values are \
resolved from multiple sources — defaults, config files, environment variables, \
command-line flags, and secret managers — showing override precedence.

Present flows with clear annotations for subprocess creation, environment \
variable inheritance, and exit code propagation.
"""

_LANG_INFRA_MERMAID = """\
## Language Expert: Infrastructure — Mermaid Diagrams

Generate Mermaid diagrams for infrastructure patterns:

1. **Infrastructure Topology:** Create deployment diagrams showing cloud \
resources (VPCs, subnets, load balancers, compute instances, databases) and \
their network connectivity. Annotate security groups and ingress/egress rules.

2. **Terraform Dependency Graph:** Show resource dependencies as a directed \
graph. Annotate with resource types and key attributes. Highlight resources \
that trigger replacement on change. Show module boundaries.

3. **CI/CD Pipeline Diagram:** Create flowcharts showing pipeline stages, \
parallel jobs, conditional paths, and approval gates. Annotate with estimated \
execution times and failure handling.

4. **Database Schema ER Diagram:** Generate entity-relationship diagrams from \
SQL DDL. Show tables, columns, primary keys, foreign keys, and indexes. \
Annotate with data types and constraints.

5. **Network Flow Diagram:** Show request routing from DNS through CDN, \
load balancer, application tier, cache, and database. Annotate with protocols, \
ports, and TLS termination points.

Use standard Mermaid syntax. For cloud architecture, use subgraphs to represent \
VPCs, availability zones, and security boundaries.
"""

_LANG_INFRA_REQUIREMENT = """\
## Language Expert: Infrastructure — Requirements Extraction

Extract requirements from infrastructure code:

1. **Cloud Provider Requirements:** Extract AWS/GCP/Azure resource requirements \
from Terraform files, CloudFormation templates, or cloud SDK usage. Document \
required service quotas, region availability, and IAM permissions.

2. **Runtime Environment Requirements:** Extract OS, shell, and tool version \
requirements. Identify Docker base images and their version constraints. \
Document required CLI tools (aws, kubectl, terraform, helm) and their \
minimum versions.

3. **Network Requirements:** Extract port mappings, DNS records, TLS \
certificate requirements, and firewall rules. Document ingress/egress \
requirements and VPN/peering connectivity needs.

4. **Database Requirements:** Extract schema requirements, storage sizing, \
backup/retention policies, and replication configurations. Document connection \
pool sizes and performance tier requirements.

5. **Security & Compliance Requirements:** Extract encryption requirements \
(at-rest, in-transit), access control policies, audit logging configurations, \
and compliance framework adherence (SOC2, HIPAA, GDPR) implied by the \
infrastructure configuration.

Present requirements grouped by cloud provider, networking, compute, storage, \
and security with Terraform resource references.
"""

_LANG_INFRA_STATIC = """\
## Language Expert: Infrastructure — Static Analysis

Perform deep semantic static analysis for infrastructure code:

1. **Shell Script Safety Analysis:** Check for unquoted variables, missing \
`set -euo pipefail`, unsafe temporary file creation (use `mktemp`), and \
broken pipe handling. Verify `shellcheck` compliance. Flag POSIX portability \
issues for scripts that claim `#!/bin/sh`.

2. **SQL Safety Analysis:** Identify SQL injection vectors in dynamic queries. \
Check for missing transaction boundaries around multi-statement operations. \
Flag `SELECT *` in production code. Verify index coverage for `WHERE` and \
`JOIN` clauses. Check for N+1 query patterns.

3. **Terraform Validation:** Check for missing variable validation blocks. \
Identify resources without lifecycle rules that need them. Flag security \
group rules that are overly permissive (`0.0.0.0/0`). Verify state locking \
is configured.

4. **YAML/JSON Schema Validation:** Verify configuration files against their \
schemas (Kubernetes manifests, Docker Compose, GitHub Actions). Flag deprecated \
API versions. Check for required fields with missing values.

5. **Path Traversal & File Safety:** Identify path construction from user \
input without canonicalisation. Flag `../` traversal opportunities. Check \
`chmod`/`chown` for overly permissive settings. Verify heredoc delimiters \
don't conflict with content.

Present findings with ShellCheck codes (SC*), tfsec rule IDs, and SQL \
anti-pattern references.
"""

_LANG_INFRA_COMMENT = """\
## Language Expert: Infrastructure — PR Review Comments

Write PR review comments for infrastructure code:

1. **Shell Safety Comments:** Flag unquoted variables and suggest `"$var"`. \
Comment on missing `set -euo pipefail`. Suggest `mktemp` for temp files. \
Flag `eval` and suggest safer alternatives. Reference ShellCheck codes.

2. **Terraform Comments:** Flag hardcoded values that should be variables. \
Comment on missing `lifecycle` blocks. Suggest `count`/`for_each` for \
resource iteration. Flag missing `depends_on` for implicit dependencies. \
Recommend `terraform fmt` and `tflint`.

3. **SQL Comments:** Flag unparameterised queries. Comment on missing indexes \
for new columns used in WHERE clauses. Suggest `EXISTS` over `COUNT(*) > 0`. \
Flag implicit type conversions in joins. Recommend query plan analysis.

4. **YAML/Config Comments:** Flag unquoted strings that could be misinterpreted. \
Comment on missing schema versions. Suggest anchors/aliases for repeated \
values. Flag secrets in plaintext config.

5. **CI/CD Pipeline Comments:** Flag missing caching, unnecessary step \
execution, and missing failure notifications. Suggest matrix builds for \
multi-platform testing. Comment on missing artifact retention policies.

Write comments with specific tool references (ShellCheck, tfsec, sqlfluff, \
yamllint) and rule IDs.
"""

_LANG_INFRA_COMMIT = """\
## Language Expert: Infrastructure — Commit Analysis

Analyse commit history in infrastructure codebases:

1. **Infrastructure Evolution:** Track cloud resource additions, modifications, \
and removals over time. Identify scaling events (instance size changes, replica \
increases). Map migration from one cloud service to another.

2. **Security Posture Changes:** Track security group rule changes, IAM policy \
modifications, and encryption enablement. Identify commits that widened access \
and whether they were later restricted. Flag temporary security relaxations \
that were never reverted.

3. **Schema Migration History:** Track database schema evolution — column \
additions, type changes, index modifications. Identify breaking schema changes \
and their corresponding application code changes. Flag missing rollback \
migrations.

4. **CI/CD Pipeline Evolution:** Track pipeline configuration changes — new \
stages, changed triggers, modified deployment strategies. Identify commits \
that fixed pipeline failures and the root causes.

5. **Configuration Drift:** Identify commits that changed configuration values \
(timeouts, limits, feature flags). Track environment-specific configuration \
divergence. Flag commits that changed production config without corresponding \
staging changes.

Present analysis as an infrastructure timeline highlighting scaling decisions, \
security improvements, and operational maturity progression.
"""

# ===================================================================
# 9. GENERIC (language-agnostic)
# ===================================================================

_LANG_GENERIC_BUG = """\
## Language Expert: Generic — Bug Analysis

Apply language-agnostic bug analysis techniques:

1. **Input Validation & Boundary Conditions:** Check every function's \
handling of edge-case inputs — empty strings, zero values, negative numbers, \
maximum-size inputs, Unicode characters, null/nil/None/undefined. Verify \
that public API entry points validate inputs before processing.

2. **Error Handling Completeness:** Trace every error path. Verify errors \
are caught, logged with context, and reported to callers. Flag swallowed \
exceptions, generic catch-all handlers, and error messages that leak \
implementation details to end users.

3. **Concurrency & Race Conditions:** Identify shared mutable state \
accessed from multiple threads or processes. Check for time-of-check-to-time-of-use \
(TOCTOU) races. Verify atomic operations where needed. Flag optimistic \
concurrency without retry logic.

4. **Logic Errors & Off-By-One:** Check loop boundaries, array indexing, \
range calculations, and fence-post errors. Verify comparison operators \
(< vs. <=). Check for inverted boolean logic and De Morgan's law violations.

5. **Resource Management:** Verify every acquired resource (file handles, \
connections, locks, memory) has a guaranteed release path, even when \
exceptions occur. Check for resource exhaustion under load (connection \
pool depletion, file descriptor limits).

Present each bug with severity (critical/high/medium/low), the trigger \
condition, and a minimal fix.
"""

_LANG_GENERIC_DESIGN = """\
## Language Expert: Generic — Code Design

Evaluate architecture and design with language-agnostic principles:

1. **Separation of Concerns:** Assess whether the code separates business \
logic from infrastructure (I/O, persistence, networking). Check for mixed \
responsibilities — functions that both compute results and perform side effects. \
Evaluate the dependency direction (domain should not depend on infrastructure).

2. **Coupling & Cohesion:** Evaluate module coupling — do changes in one \
module cascade to many others? Assess cohesion — do modules group related \
functionality or unrelated utilities? Check for Feature Envy (functions \
that use more of another module's data than their own).

3. **Abstraction Quality:** Assess whether abstractions model the domain \
accurately. Flag leaky abstractions that expose implementation details. \
Check for premature abstraction (interfaces with single implementations) \
and missing abstraction (duplicated logic).

4. **Error Strategy Consistency:** Evaluate whether the codebase uses \
exceptions, error codes, or result types consistently. Check for mixed \
strategies that confuse callers. Assess whether errors carry enough \
context for debugging and monitoring.

5. **Testability Assessment:** Evaluate whether the code is testable in \
isolation. Identify hard-to-test patterns — static method calls, hidden \
dependencies, temporal coupling, and non-deterministic behaviour. Suggest \
dependency injection and interface extraction.

Provide a design quality assessment with specific refactoring suggestions \
prioritised by impact and effort.
"""

_LANG_GENERIC_FLOW = """\
## Language Expert: Generic — Code Flow

Trace execution flow using language-agnostic techniques:

1. **Happy Path Trace:** Follow the primary success path from entry point \
to output. Document each function call, data transformation, and decision \
point. Show the data shape at each stage.

2. **Error Path Enumeration:** For each step in the happy path, enumerate \
what can go wrong. Trace each error path to its handling point. Identify \
error paths that lead to inconsistent state (partially completed operations).

3. **Data Flow & Transformation:** Track key data objects from creation \
through transformation to consumption. Show where data is validated, \
enriched, filtered, or aggregated. Identify where data crosses trust \
boundaries (user input -> business logic -> persistence).

4. **Control Flow Complexity:** Map branching logic — nested conditionals, \
loops, early returns, and fallthrough. Calculate cyclomatic complexity for \
key functions. Identify functions with excessive branching that should be \
decomposed.

5. **External Integration Points:** Identify all external calls (HTTP APIs, \
databases, file system, message queues). Show timeout, retry, and circuit \
breaker patterns. Identify calls that lack error handling or timeout configuration.

Present flows as numbered steps with clear entry/exit points, annotating \
where concurrency, caching, or batching occurs.
"""

_LANG_GENERIC_MERMAID = """\
## Language Expert: Generic — Mermaid Diagrams

Generate clear, language-agnostic Mermaid diagrams:

1. **System Context Diagram (C4 Level 1):** Show the system under analysis \
as a central box with external actors (users, external systems, APIs) connected \
by arrows annotated with protocols and data flows.

2. **Container Diagram (C4 Level 2):** Decompose the system into containers \
(applications, databases, message brokers). Show communication protocols \
between containers. Annotate with technology choices.

3. **Sequence Diagrams for Key Flows:** Create sequence diagrams for the 3-5 \
most important user-facing or system-critical flows. Show participant lifelines, \
synchronous/asynchronous calls, and error responses.

4. **Data Flow Diagram:** Show how data enters, transforms, and exits the \
system. Annotate transformation nodes with the business rule applied. \
Highlight data stores and their access patterns.

5. **Error Handling Flowchart:** Create a flowchart showing the error handling \
strategy — from error detection through classification, logging, user \
notification, and recovery/retry.

Keep diagrams focused and readable. Use subgraphs for logical grouping. \
Ensure all diagrams compile in standard Mermaid syntax.
"""

_LANG_GENERIC_REQUIREMENT = """\
## Language Expert: Generic — Requirements Extraction

Extract requirements using language-agnostic techniques:

1. **Functional Requirements:** Extract what the code does — input/output \
contracts, business rules encoded in conditionals, validation constraints, \
and state machine transitions. Document each requirement with its source \
location.

2. **Non-Functional Requirements:** Extract performance requirements (timeouts, \
batch sizes, cache TTLs), reliability requirements (retry counts, circuit \
breaker thresholds), and scalability requirements (connection pool sizes, \
queue depths).

3. **Security Requirements:** Extract authentication mechanisms, authorization \
checks, input validation rules, output encoding, and cryptographic operations. \
Document the trust model — what is trusted, what is validated.

4. **Integration Requirements:** Extract external API contracts, database \
schema assumptions, file format specifications, and message queue protocols. \
Document expected latencies and availability requirements.

5. **Operational Requirements:** Extract logging points, health check endpoints, \
metrics emission, configuration parameters, and deployment constraints. \
Document monitoring and alerting requirements implied by the code.

Present requirements as structured cards with: ID, type (functional, \
non-functional, security, integration, operational), source location, \
confidence level, and any ambiguity notes.
"""

_LANG_GENERIC_STATIC = """\
## Language Expert: Generic — Static Analysis

Perform deep semantic static analysis using language-agnostic techniques:

1. **Data Flow Analysis:** Track variables from definition to every use. \
Identify unused variables, redundant assignments, and variables used before \
definition. Trace tainted data from external sources to sensitive sinks.

2. **Control Flow Analysis:** Identify unreachable code, infinite loops, \
and dead branches. Check for consistent return value handling across all \
code paths. Verify that all switch/match cases are handled.

3. **Complexity Analysis:** Calculate cyclomatic complexity for each function. \
Identify functions exceeding threshold (>10). Flag deeply nested conditionals \
(>3 levels). Suggest decomposition strategies for complex functions.

4. **Duplication Detection:** Identify copy-pasted code blocks, near-duplicate \
functions, and repeated patterns that should be extracted into shared utilities. \
Assess whether duplication is accidental or intentional (copy-paste-modify \
anti-pattern vs. deliberate decoupling).

5. **Naming & Convention Analysis:** Check naming consistency — are similar \
concepts named similarly? Flag misleading names (boolean variables without \
is/has prefix, functions with side effects named like queries). Check for \
consistent abbreviation and acronym usage.

Present findings with severity, confidence, and suggested automated tools \
that could catch each issue in CI.
"""

_LANG_GENERIC_COMMENT = """\
## Language Expert: Generic — PR Review Comments

Write PR review comments using universal best practices:

1. **Clarity & Readability Comments:** Comment on naming that could be \
improved, complex expressions that need decomposition, and missing or \
misleading comments. Suggest self-documenting code patterns over comments.

2. **Error Handling Comments:** Flag missing error handling, swallowed errors, \
and error messages without context. Suggest structured logging with correlation \
IDs. Comment on retry strategies and timeout handling.

3. **Testing Comments:** Identify untested code paths, missing edge-case tests, \
and test assertions that are too broad. Suggest specific test cases for \
boundary conditions, error paths, and integration points.

4. **Security Comments:** Flag hardcoded secrets, missing input validation, \
unparameterised queries, and missing output encoding. Suggest security headers, \
rate limiting, and audit logging.

5. **Performance Comments:** Flag unnecessary work in loops, missing \
pagination for large data sets, N+1 query patterns, and missing caching \
for expensive computations. Suggest profiling before optimisation.

Write comments that are constructive, specific, and include code suggestions. \
Cite established principles (DRY, YAGNI, KISS) when applicable.
"""

_LANG_GENERIC_COMMIT = """\
## Language Expert: Generic — Commit Analysis

Analyse commit history using language-agnostic techniques:

1. **Commit Hygiene:** Evaluate commit message quality — are they descriptive? \
Do they follow conventional commit format? Check for atomic commits vs. \
kitchen-sink commits that mix features, fixes, and refactoring.

2. **Change Velocity & Hotspots:** Identify files and modules that change \
most frequently. Correlate change frequency with bug fixes — frequently \
changed modules with many bug-fix commits indicate design problems.

3. **Refactoring Trends:** Track extract/rename/move refactorings over time. \
Identify whether the codebase is improving (decreasing complexity, better \
naming) or degrading (growing functions, increasing coupling).

4. **Dependency Changes:** Track when new dependencies were added, what they \
replaced, and whether they were evaluated properly. Identify dependency churn \
(frequent switches between alternatives).

5. **Collaboration Patterns:** Analyse who changes what — are there knowledge \
silos (only one person changes certain modules)? Do bug fixes come from \
different people than original authors (indicating unclear code)?

Present the analysis as a codebase health narrative highlighting trends, \
risks, and recommendations for improving development practices.
"""

# ---------------------------------------------------------------------------
# Assemble all 72 templates
# ---------------------------------------------------------------------------

LANGUAGE_EXPERT_TEMPLATES: list[PromptTemplate] = [
    # --- dynamic_scripting ---
    _t("dynamic_scripting", "bug_analysis", "Type safety, GIL, monkey patching, mutable defaults", _LANG_DYNAMIC_BUG),
    _t("dynamic_scripting", "code_design", "Duck typing protocols, module organisation, DI", _LANG_DYNAMIC_DESIGN),
    _t("dynamic_scripting", "code_flow", "Dynamic dispatch, generators, decorator chains", _LANG_DYNAMIC_FLOW),
    _t("dynamic_scripting", "mermaid", "MRO graphs, async flow, module dependencies", _LANG_DYNAMIC_MERMAID),
    _t("dynamic_scripting", "requirement", "Type contracts, runtime env, concurrency needs", _LANG_DYNAMIC_REQUIREMENT),
    _t("dynamic_scripting", "static_analysis", "Type inference, taint analysis, resource leaks", _LANG_DYNAMIC_STATIC),
    _t("dynamic_scripting", "comment_generator", "Type hints, idioms, security, test gaps", _LANG_DYNAMIC_COMMENT),
    _t("dynamic_scripting", "commit_analysis", "Type annotation evolution, dependency churn", _LANG_DYNAMIC_COMMIT),

    # --- systems ---
    _t("systems", "bug_analysis", "Memory safety, UB, RAII, ownership, concurrency", _LANG_SYSTEMS_BUG),
    _t("systems", "code_design", "Ownership model, abstraction layers, ABI design", _LANG_SYSTEMS_DESIGN),
    _t("systems", "code_flow", "Pointer chains, stack/heap, exception/longjmp paths", _LANG_SYSTEMS_FLOW),
    _t("systems", "mermaid", "Memory ownership, struct layout, concurrency diagrams", _LANG_SYSTEMS_MERMAID),
    _t("systems", "requirement", "Memory budget, platform requirements, ABI contracts", _LANG_SYSTEMS_REQUIREMENT),
    _t("systems", "static_analysis", "Lifetime analysis, integer safety, null tracking", _LANG_SYSTEMS_STATIC),
    _t("systems", "comment_generator", "Memory safety, UB warnings, performance, portability", _LANG_SYSTEMS_COMMENT),
    _t("systems", "commit_analysis", "Memory safety evolution, ABI breaks, security patches", _LANG_SYSTEMS_COMMIT),

    # --- jvm ---
    _t("jvm", "bug_analysis", "Thread safety, null handling, resource leaks, streams", _LANG_JVM_BUG),
    _t("jvm", "code_design", "SOLID, generics, concurrency architecture, DI", _LANG_JVM_DESIGN),
    _t("jvm", "code_flow", "DI wiring, exception propagation, reactive chains", _LANG_JVM_FLOW),
    _t("jvm", "mermaid", "Class hierarchies, Spring beans, thread diagrams", _LANG_JVM_MERMAID),
    _t("jvm", "requirement", "JVM runtime, framework deps, API contracts, security", _LANG_JVM_REQUIREMENT),
    _t("jvm", "static_analysis", "Null safety, concurrency, generics, performance", _LANG_JVM_STATIC),
    _t("jvm", "comment_generator", "Null handling, concurrency, API design, testing", _LANG_JVM_COMMENT),
    _t("jvm", "commit_analysis", "Java version migration, framework upgrades, schema", _LANG_JVM_COMMIT),

    # --- dotnet ---
    _t("dotnet", "bug_analysis", "Async deadlocks, IDisposable, nullable, LINQ traps", _LANG_DOTNET_BUG),
    _t("dotnet", "code_design", "DI architecture, async consistency, EF design, API surface", _LANG_DOTNET_DESIGN),
    _t("dotnet", "code_flow", "ASP.NET pipeline, async state machine, DI resolution", _LANG_DOTNET_FLOW),
    _t("dotnet", "mermaid", "Clean architecture, middleware pipeline, EF relationships", _LANG_DOTNET_MERMAID),
    _t("dotnet", "requirement", ".NET runtime, NuGet deps, config, infrastructure", _LANG_DOTNET_REQUIREMENT),
    _t("dotnet", "static_analysis", "Nullable flow, async correctness, disposal, LINQ safety", _LANG_DOTNET_STATIC),
    _t("dotnet", "comment_generator", "Async patterns, DI lifetime, nullable safety, modern C#", _LANG_DOTNET_COMMENT),
    _t("dotnet", "commit_analysis", "Framework migration, NuGet evolution, EF migrations", _LANG_DOTNET_COMMIT),

    # --- go ---
    _t("go", "bug_analysis", "Goroutine leaks, channel deadlocks, error handling, defer", _LANG_GO_BUG),
    _t("go", "code_design", "Interface design, package structure, error design, testing", _LANG_GO_DESIGN),
    _t("go", "code_flow", "Goroutine lifecycle, error propagation, HTTP handler chain", _LANG_GO_FLOW),
    _t("go", "mermaid", "Goroutine communication, package deps, interface map", _LANG_GO_MERMAID),
    _t("go", "requirement", "Go version, module deps, runtime config, concurrency", _LANG_GO_REQUIREMENT),
    _t("go", "static_analysis", "Race conditions, error paths, resource leaks, nil safety", _LANG_GO_STATIC),
    _t("go", "comment_generator", "Error handling, goroutine safety, idioms, API design", _LANG_GO_COMMENT),
    _t("go", "commit_analysis", "Go version adoption, dependency management, concurrency", _LANG_GO_COMMIT),

    # --- frontend ---
    _t("frontend", "bug_analysis", "XSS, prototype pollution, closures, event loop, state", _LANG_FRONTEND_BUG),
    _t("frontend", "code_design", "Component architecture, TypeScript, bundle, CSS, API layer", _LANG_FRONTEND_DESIGN),
    _t("frontend", "code_flow", "Render cycle, event propagation, data fetching, SSR", _LANG_FRONTEND_FLOW),
    _t("frontend", "mermaid", "Component tree, state machines, event flow, build pipeline", _LANG_FRONTEND_MERMAID),
    _t("frontend", "requirement", "Browser support, framework deps, API contracts, a11y", _LANG_FRONTEND_REQUIREMENT),
    _t("frontend", "static_analysis", "Type safety, security, hooks, bundle size, a11y", _LANG_FRONTEND_STATIC),
    _t("frontend", "comment_generator", "Security, performance, TypeScript, a11y, testing", _LANG_FRONTEND_COMMENT),
    _t("frontend", "commit_analysis", "Framework migration, dependency churn, TS adoption", _LANG_FRONTEND_COMMIT),

    # --- functional ---
    _t("functional", "bug_analysis", "Pattern completeness, laziness, processes, immutability", _LANG_FUNCTIONAL_BUG),
    _t("functional", "code_design", "ADT design, module organisation, effects, concurrency", _LANG_FUNCTIONAL_DESIGN),
    _t("functional", "code_flow", "Composition chains, pattern dispatch, recursion, messages", _LANG_FUNCTIONAL_FLOW),
    _t("functional", "mermaid", "Pipelines, supervision trees, ADT diagrams, process flow", _LANG_FUNCTIONAL_MERMAID),
    _t("functional", "requirement", "Runtime/compiler, type system, concurrency, integrations", _LANG_FUNCTIONAL_REQUIREMENT),
    _t("functional", "static_analysis", "Totality, purity, space leaks, process safety", _LANG_FUNCTIONAL_STATIC),
    _t("functional", "comment_generator", "Totality, type design, effects, OTP patterns", _LANG_FUNCTIONAL_COMMENT),
    _t("functional", "commit_analysis", "Type system evolution, effect management, OTP changes", _LANG_FUNCTIONAL_COMMIT),

    # --- infrastructure ---
    _t("infrastructure", "bug_analysis", "Shell injection, SQL injection, YAML traps, secrets", _LANG_INFRA_BUG),
    _t("infrastructure", "code_design", "Shell structure, Terraform modules, schema, CI/CD", _LANG_INFRA_DESIGN),
    _t("infrastructure", "code_flow", "Shell execution, Terraform apply, CI/CD pipeline", _LANG_INFRA_FLOW),
    _t("infrastructure", "mermaid", "Infrastructure topology, Terraform graph, ER diagrams", _LANG_INFRA_MERMAID),
    _t("infrastructure", "requirement", "Cloud provider, runtime env, network, DB, security", _LANG_INFRA_REQUIREMENT),
    _t("infrastructure", "static_analysis", "Shell safety, SQL safety, Terraform validation, YAML", _LANG_INFRA_STATIC),
    _t("infrastructure", "comment_generator", "Shell safety, Terraform, SQL, YAML, CI/CD", _LANG_INFRA_COMMENT),
    _t("infrastructure", "commit_analysis", "Infrastructure evolution, security posture, schema", _LANG_INFRA_COMMIT),

    # --- generic ---
    _t("generic", "bug_analysis", "Input validation, error handling, concurrency, logic errors", _LANG_GENERIC_BUG),
    _t("generic", "code_design", "Separation of concerns, coupling, abstraction, testability", _LANG_GENERIC_DESIGN),
    _t("generic", "code_flow", "Happy path, error paths, data flow, complexity, integrations", _LANG_GENERIC_FLOW),
    _t("generic", "mermaid", "C4 diagrams, sequence diagrams, data flow, error handling", _LANG_GENERIC_MERMAID),
    _t("generic", "requirement", "Functional, non-functional, security, integration, ops", _LANG_GENERIC_REQUIREMENT),
    _t("generic", "static_analysis", "Data flow, control flow, complexity, duplication, naming", _LANG_GENERIC_STATIC),
    _t("generic", "comment_generator", "Clarity, error handling, testing, security, performance", _LANG_GENERIC_COMMENT),
    _t("generic", "commit_analysis", "Commit hygiene, hotspots, refactoring, dependencies", _LANG_GENERIC_COMMIT),
]

# ---------------------------------------------------------------------------
# Lookup index: (family, agent) -> PromptTemplate
# ---------------------------------------------------------------------------

LANGUAGE_INDEX: dict[tuple[str, str], PromptTemplate] = {}
for _tmpl in LANGUAGE_EXPERT_TEMPLATES:
    _family = _tmpl.label.split("(")[1].rstrip(")")
    LANGUAGE_INDEX[(_family, _tmpl.agent)] = _tmpl
