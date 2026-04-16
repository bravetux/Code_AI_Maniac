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

"""Performance Deep Dive prompt templates — universal + language-family addons."""

from __future__ import annotations

from config.prompt_templates import PromptTemplate


def _t(agent: str, description: str, text: str) -> PromptTemplate:
    return PromptTemplate(
        category="Performance Deep Dive",
        agent=agent,
        label="Performance Deep Dive",
        description=description,
        prompt_text=text,
    )


# ---------------------------------------------------------------------------
# Universal templates — one per agent, language-agnostic
# ---------------------------------------------------------------------------

_PERF_BUG = """\
## Performance Deep Dive

Analyse the code for performance bugs using these five lenses:

1. **Algorithmic Complexity Audit:** Identify every loop, recursion, and collection \
operation. Determine actual time complexity (not just theoretical). Look for \
hidden quadratic behaviour: nested iterations, repeated linear searches inside \
loops, cartesian products built by accident. Estimate the input size at which \
each hot spot becomes a problem (e.g., "O(n^2) — painful above ~10 000 items").

2. **Memory Leak & Allocation Analysis:** Trace object lifetimes. Find references \
that prevent garbage collection: closures capturing large scopes, growing caches \
without eviction, event listeners never removed, circular references. Estimate \
retained memory in MB for typical workloads. Flag unnecessary copies of large \
buffers or strings.

3. **I/O & Network Bottleneck Detection:** Locate every I/O call — disk, network, \
database. Are any called inside a loop (N+1 pattern)? Are responses awaited \
sequentially when they could be parallelised? Estimate wasted wall-clock time \
in milliseconds for typical payloads.

4. **Caching & Memoisation Gaps:** Identify pure or near-pure computations whose \
results are discarded and recomputed. Look for repeated identical queries, \
redundant API calls, and deterministic transforms applied to the same input \
multiple times. Estimate the cache hit-rate potential and latency savings.

5. **Concurrency & Contention Issues:** Find shared mutable state accessed without \
proper synchronisation. Identify lock granularity problems, thread-pool \
starvation, priority inversion, and unnecessary serialisation of parallel work. \
Estimate throughput impact in ops/sec or request latency added.

For every finding, provide:
- Location (file + line or function name)
- Estimated impact (ms saved, MB freed, ops/sec gained)
- Concrete fix with a code sketch"""

_PERF_DESIGN = """\
## Performance Deep Dive

Evaluate the code's design for performance and scalability:

1. **Scalability Architecture Review:** Does the design scale horizontally? Identify \
single points of contention: shared mutable state, global locks, centralised \
queues. Evaluate whether the current design supports 10x the current load \
without a rewrite. Note bottlenecks that would appear first.

2. **Caching Strategy Evaluation:** Map every data access path. Is caching applied \
at the right layer (in-process, distributed, CDN)? Are TTLs appropriate? Is \
cache invalidation correct, or are stale reads possible? Identify data that \
is fetched repeatedly but changes infrequently.

3. **Data Structure & Collection Choices:** For each major data structure, evaluate \
whether the choice matches the access pattern. Are lookups O(n) when they \
should be O(1)? Are sorted structures used where insertion order suffices? \
Would a specialised structure (bloom filter, trie, skip list) outperform \
the current choice?

4. **Connection & Resource Pooling:** Identify external resources (DB, HTTP, file \
handles). Are connections pooled? Are pool sizes tuned? Is there back-pressure \
when the pool is exhausted, or do requests queue unboundedly? Flag any \
resource opened in a request path and never explicitly released.

5. **Lazy Loading & Batching Opportunities:** Find eagerly loaded data that is not \
always needed. Identify N sequential calls that could be batched into one. \
Evaluate whether pagination or streaming would reduce memory pressure.

Prioritise recommendations by expected latency or throughput improvement. \
Provide before/after design sketches for the top 3 findings."""

_PERF_FLOW = """\
## Performance Deep Dive

Trace the code's execution to map performance characteristics:

1. **Hot Path Identification:** Follow the main request/execution path from entry \
to exit. Measure or estimate wall-clock time per stage. Identify the 20% of \
code responsible for 80% of execution time. Mark each stage as CPU-bound, \
I/O-bound, or wait-bound.

2. **I/O Boundary Mapping:** List every point where execution crosses an I/O \
boundary (network, disk, IPC, database). For each boundary, note: is it \
synchronous or asynchronous? Is it batched? What is the expected latency? \
Are there serial chains of I/O that could be parallelised?

3. **Bottleneck & Stall Analysis:** Identify stages where throughput drops or \
latency spikes. Look for: lock contention, GC pauses, thread pool exhaustion, \
connection pool waits, rate limiting, backpressure. Estimate the queue depth \
or wait time at each bottleneck.

4. **Parallelisation Opportunities:** Map data dependencies between stages. Which \
stages are independent and could run concurrently? What is the theoretical \
speedup from parallelising them (Amdahl's Law estimate)? What synchronisation \
would be required?

5. **Cold Start & Warmup Analysis:** What happens on first invocation? Identify \
lazy-initialisation costs, JIT compilation delays, cache misses, connection \
establishment. Estimate cold-start penalty vs steady-state latency.

Present findings as an annotated execution timeline. For each stage, show: \
name, type (CPU/IO/wait), estimated duration, and improvement opportunity."""

_PERF_MERMAID = """\
## Performance Deep Dive

Generate performance-focused Mermaid diagrams:

1. **Hot Path Sequence Diagram:** Create a sequence diagram of the critical request \
path. Annotate each arrow with estimated latency (ms). Use colour/style \
annotations to distinguish: fast (<10ms) as normal, moderate (10-100ms) \
as dashed, slow (>100ms) as bold/red. Add notes for I/O waits and \
parallelisable sections.

2. **Resource Flow Diagram:** Create a flowchart showing how data flows through \
caches, pools, queues, and external services. Annotate each node with \
throughput capacity and each edge with typical payload size. Highlight \
edges where data is copied unnecessarily.

3. **Bottleneck Architecture Diagram:** Create a component diagram with \
performance annotations. Mark each component with its scaling characteristic \
(stateless/stateful, CPU/IO bound). Draw contention points as red nodes. \
Show pool sizes, queue depths, and connection limits.

4. **Concurrency Timeline Diagram:** If concurrent execution exists, create a \
Gantt-style diagram showing parallel tasks, synchronisation points, and \
idle/wait periods. Highlight time lost to serialisation or lock contention.

5. **Capacity Planning Diagram:** Create a diagram showing resource utilisation \
at current load vs projected load (2x, 5x, 10x). Annotate which component \
saturates first and at what load level.

Use Mermaid syntax exclusively. Add `%%` comments explaining performance \
significance of each diagram element. Ensure diagrams render correctly."""

_PERF_REQUIREMENT = """\
## Performance Deep Dive

Extract and evaluate performance requirements from the code:

1. **SLA & Latency Budget Extraction:** Identify explicit or implied latency \
requirements: timeouts, deadline parameters, SLA comments, retry policies. \
For each endpoint or operation, derive the implicit latency budget from \
timeout configurations. Flag operations with no timeout (unbounded latency).

2. **Throughput & Capacity Targets:** Extract rate limits, batch sizes, pool \
sizes, queue lengths, and worker counts. Infer the maximum throughput the \
system is designed to handle. Identify where throughput is artificially \
constrained by configuration rather than architecture.

3. **Resource Consumption Limits:** Find memory limits, file descriptor caps, \
connection pool maxima, disk quota checks. Are these limits explicitly set \
or defaulted? Are they appropriate for the expected workload? Flag resources \
with no upper bound.

4. **Scaling Requirements & Assumptions:** Identify assumptions about deployment \
topology: single instance vs multi-instance, shared state requirements, \
session affinity. Document what must be true for horizontal scaling to work. \
Flag hard-coded values that prevent scaling (e.g., in-process caches without \
invalidation).

5. **Performance Testing Gaps:** Based on the extracted requirements, identify \
which performance characteristics are untested. Are there load tests? \
Benchmarks? Latency assertions? Recommend the top 5 performance tests that \
should be added, with specific metrics and thresholds.

Output a structured performance requirements document with: requirement ID, \
description, current value, recommended value, risk if unmet."""

_PERF_STATIC = """\
## Performance Deep Dive

Detect performance anti-patterns through static analysis:

1. **Quadratic & Super-Linear Patterns:** Scan for nested loops over the same \
collection, repeated linear searches, string concatenation in loops, \
recursive calls without memoisation. For each finding, state the actual \
complexity and the input size at which it degrades noticeably.

2. **Unnecessary Allocation & Copying:** Find objects created inside hot loops \
that could be reused, defensive copies that are never mutated, string \
conversions applied repeatedly to the same value, collections built only \
to be iterated once. Estimate allocations per second at typical load.

3. **Blocking & Synchronous Anti-Patterns:** Identify synchronous I/O in async \
contexts, blocking calls on the event loop or main thread, sleep/poll loops \
replacing event-driven waits, DNS resolution in the request path. Flag each \
with estimated blocking duration.

4. **Missing Index & Query Anti-Patterns:** If database queries are present, \
look for: full table scans (no WHERE or unindexed columns), SELECT *, \
queries inside loops (N+1), missing LIMIT on potentially large result sets, \
no pagination. Estimate row counts and I/O impact.

5. **Unbounded Growth & Resource Leaks:** Find collections that grow without \
bound (maps used as caches without eviction, logs appended without rotation). \
Identify resources opened in loops but closed only on the happy path. \
Estimate memory growth rate (MB/hour) under sustained load.

For each anti-pattern, provide: location, severity (critical/high/medium/low), \
estimated performance impact, and a concrete fix."""

_PERF_COMMENT = """\
## Performance Deep Dive

Write performance-focused PR review comments:

1. **Impact-First Comments:** Lead every comment with the estimated performance \
impact: "This adds ~200ms per request" or "Allocates ~5MB per call that \
could be pooled." Quantify in ms, MB, ops/sec, or percentage degradation. \
Avoid vague statements like "this might be slow."

2. **Regression Detection:** Compare the changed code against the previous \
implementation. Identify: new N+1 queries, increased algorithmic complexity, \
additional I/O calls, larger payloads, removed caching. For each regression, \
estimate the before/after performance difference.

3. **Load-Sensitive Review:** Consider the comment in context of expected load. \
A 1ms overhead is irrelevant for a nightly batch job but critical in a \
hot loop processing 100k items/sec. State the load context and scale \
the severity accordingly.

4. **Actionable Suggestions:** Every performance concern must include a concrete \
fix or alternative approach. Provide code snippets where helpful. Reference \
specific APIs, data structures, or patterns that would improve performance. \
Estimate the improvement from each suggestion.

5. **Benchmark Requests:** For non-obvious performance claims, request benchmark \
evidence. Suggest specific benchmark scenarios: input sizes, concurrency \
levels, and metrics to measure. Recommend profiling tools appropriate to \
the tech stack.

Use a consistent format: [PERF: severity] Location — Impact — Suggestion. \
Group related comments. Acknowledge when a trade-off (readability vs speed) \
is acceptable."""

_PERF_COMMIT = """\
## Performance Deep Dive

Analyse commits for their performance impact:

1. **Dependency Change Analysis:** For added or upgraded dependencies, evaluate: \
bundle size impact (KB/MB added), cold start penalty, known performance \
characteristics. Flag dependencies that pull in heavy transitive trees or \
include native compilation steps that slow CI.

2. **Algorithmic Change Detection:** Identify changes to loops, data structures, \
sorting, searching, or caching logic. Compare before/after time complexity. \
Look for subtle regressions: a list replacing a set, a linear scan replacing \
a hash lookup, an eager load replacing a lazy one.

3. **Database & Schema Migration Impact:** For migration files or query changes, \
assess: will the migration lock tables? For how long at current table size? \
Do new queries hit existing indexes? Are new indexes added that will slow \
writes? Estimate migration duration and query plan changes.

4. **Configuration & Infrastructure Changes:** Evaluate changes to pool sizes, \
timeouts, batch sizes, retry policies, cache TTLs. Are the new values \
justified? Will they perform well under peak load? Flag configuration \
changes that trade latency for correctness or vice versa.

5. **Cumulative Regression Tracking:** Look at the commit in the context of \
recent history. Is there a pattern of small performance regressions that \
compound? Are performance-sensitive paths getting more complex over time? \
Flag "death by a thousand cuts" trends.

For each commit, provide: performance verdict (positive/neutral/negative), \
estimated impact magnitude, and recommended follow-up actions."""

# ---------------------------------------------------------------------------
# Language-family performance addons (4 agents x 8 families = 32)
# ---------------------------------------------------------------------------

# --- dynamic_scripting (Python, Ruby, Perl, Lua, PHP) ---------------------

_PERF_ADDON_DYNAMIC_BUG = """\
## Performance Addon: Dynamic Scripting

1. **GIL & Interpreter Overhead:** Identify CPU-bound code in Python/Ruby that \
is bottlenecked by the Global Interpreter Lock. Look for threading used for \
CPU work instead of multiprocessing or C extensions. Flag hot loops that \
would benefit from Cython, NumPy vectorisation, or cffi bindings.

2. **Generator vs List Materialisation:** Find list comprehensions or `list()` \
calls on large iterables that could remain as generators. Check for \
`range()` vs `xrange()` in Python 2 codebases. Identify chained \
`map()`/`filter()` that materialise intermediate lists.

3. **Object Model Overhead:** Look for classes with many instances that lack \
`__slots__` (Python) or use `OpenStruct` (Ruby). Check for excessive \
`__getattr__`/`method_missing` usage on hot paths. Flag dynamic attribute \
creation in loops.

4. **String Interning & Intern Opportunities:** Identify repeated string \
comparisons or dictionary keys that would benefit from interning. Look for \
string concatenation in loops instead of `join()` or `StringIO`. Flag \
f-string or format-string usage in logging that is evaluated even when \
the log level is disabled."""

_PERF_ADDON_DYNAMIC_DESIGN = """\
## Performance Addon: Dynamic Scripting

1. **C Extension Architecture:** Evaluate whether compute-intensive modules are \
structured to allow drop-in C/Rust extensions. Check for clear boundaries \
between orchestration code (stays in Python/Ruby) and numerical/parsing \
code (should move to native). Assess Cython, pybind11, or FFI readiness.

2. **Async I/O Design:** Review whether the I/O layer uses asyncio (Python), \
EventMachine (Ruby), or equivalent. Identify sync-in-async violations \
where blocking calls are made inside async functions. Evaluate whether \
the event loop is properly utilised or starved.

3. **Process Pool & Worker Design:** Assess whether CPU-bound work uses \
multiprocessing, Celery workers, or similar. Check for serialisation \
overhead when passing data between processes. Evaluate whether shared \
memory (e.g., `multiprocessing.shared_memory`) would reduce IPC cost."""

_PERF_ADDON_DYNAMIC_STATIC = """\
## Performance Addon: Dynamic Scripting

1. **Dynamic Dispatch Hot Paths:** Scan for `getattr()`, `eval()`, `exec()`, \
or `importlib.import_module()` called in tight loops. These bypass the \
interpreter's optimisation and add microseconds per call that compound \
at scale. Suggest static dispatch or lookup-table alternatives.

2. **Collection Misuse Patterns:** Find `in` membership tests on lists that \
should be sets, `dict.keys()` iterations in Python 2 style, and \
`sorted()` called on already-sorted data. Look for `append()` in a loop \
building a result that could use a list comprehension or `itertools`.

3. **Import-Time Side Effects:** Identify modules that perform heavy work at \
import time: database connections, file reads, large computations. These \
slow down startup and make testing brittle. Flag imports inside functions \
that are called repeatedly (import overhead per call).

4. **Regex Compilation in Loops:** Find `re.match()` or `re.search()` calls \
with literal patterns inside loops instead of pre-compiled `re.compile()`. \
Each un-compiled call re-parses the pattern. Estimate calls per second \
and cumulative overhead."""

_PERF_ADDON_DYNAMIC_FLOW = """\
## Performance Addon: Dynamic Scripting

1. **Interpreter Warm-Up Path:** Trace the startup sequence: module imports, \
decorator execution, class body evaluation. Identify slow imports (large \
packages, native extensions) and unnecessary eager initialisation. Estimate \
cold-start time contribution per import.

2. **GIL Contention Timeline:** Map concurrent threads and identify where they \
contend for the GIL. Show which stages are truly parallel (C extensions \
releasing the GIL, I/O waits) vs serialised. Estimate effective parallelism \
as a fraction of theoretical.

3. **Generator Pipeline Flow:** Trace data through generator/iterator chains. \
Identify where lazy evaluation is broken by materialisation (`list()`, \
`len()`, slicing). Map memory high-water marks along the pipeline."""

# --- systems (C, C++, Rust, Zig) -----------------------------------------

_PERF_ADDON_SYSTEMS_BUG = """\
## Performance Addon: Systems Languages

1. **Cache Line & Memory Layout:** Identify structs with poor field ordering \
that waste cache lines (padding between fields). Look for arrays of \
structs (AoS) that should be structs of arrays (SoA) for vectorisation. \
Check for false sharing in concurrent code where unrelated fields share \
a cache line. Suggest `alignas` or `#[repr(align)]` where appropriate.

2. **Allocation Pattern Analysis:** Find `malloc`/`new`/`Box::new` calls inside \
hot loops. Look for missing arena or pool allocators for small, frequent \
allocations. Identify `realloc` chains that could be avoided by pre-sizing. \
Check for stack allocations (VLAs, `alloca`) that risk stack overflow.

3. **SIMD & Vectorisation Opportunities:** Identify loops over contiguous data \
that the compiler may fail to auto-vectorise (due to aliasing, branching, \
or data dependencies). Suggest explicit SIMD intrinsics, `restrict` \
qualifiers, or Rust's `std::simd` where applicable. Estimate throughput \
gain from vectorisation.

4. **Branch Prediction & Inlining:** Find branches in hot loops with \
unpredictable patterns. Suggest `__builtin_expect`, `likely`/`unlikely` \
hints, or branchless alternatives. Identify small functions called in \
tight loops that are not marked `inline`/`#[inline]` and may not be \
inlined by the compiler."""

_PERF_ADDON_SYSTEMS_DESIGN = """\
## Performance Addon: Systems Languages

1. **Zero-Copy Architecture:** Evaluate whether the design minimises data \
copying. Check for string/buffer ownership transfers that could use \
borrowing (Rust `&[u8]`, C++ `std::string_view`, `std::span`). Assess \
whether serialisation/deserialisation avoids intermediate allocations \
(e.g., FlatBuffers, Cap'n Proto vs JSON/protobuf).

2. **Memory Allocator Strategy:** Review whether the application benefits \
from a custom allocator: jemalloc, mimalloc, arena allocators for \
request-scoped data, or slab allocators for fixed-size objects. Evaluate \
whether `mmap` is used appropriately for large files vs `read` into heap.

3. **Lock-Free & Wait-Free Design:** Assess whether concurrent data structures \
use lock-free algorithms where appropriate. Check for `std::mutex` or \
`pthread_mutex` on hot paths that could use atomics, RCU, or \
compare-and-swap. Evaluate memory ordering constraints (`Relaxed` vs \
`SeqCst` in Rust, `memory_order` in C++)."""

_PERF_ADDON_SYSTEMS_STATIC = """\
## Performance Addon: Systems Languages

1. **Unnecessary Heap Allocation:** Find `std::string`, `std::vector`, \
`String`, `Vec` where stack-allocated alternatives suffice (fixed-size \
arrays, `SmallVec`, `ArrayString`). Identify `unique_ptr`/`Box` for \
small objects that could live on the stack. Flag `new`/`malloc` without \
corresponding size justification.

2. **Missing Move Semantics:** In C++, find copies where moves would suffice: \
returning local objects by value without NRVO, passing large objects by \
value to sinks without `std::move`, copy-constructing from temporaries. \
In Rust, identify unnecessary `.clone()` calls on hot paths.

3. **Unsafe Abstraction Overhead:** Look for abstractions that add runtime \
cost: virtual dispatch in hot loops (vtable indirection), RTTI usage \
(`dynamic_cast`), exceptions for control flow. Suggest devirtualisation, \
CRTP, or sum types as alternatives. Flag Rust `dyn Trait` where \
generic monomorphisation would be faster.

4. **Compiler Hint Gaps:** Identify functions missing `[[nodiscard]]`, \
`const`/`constexpr`, `noexcept` (C++), or `#[must_use]`, `const fn` \
(Rust). These hints enable compiler optimisations and prevent accidental \
discard of expensive computations."""

_PERF_ADDON_SYSTEMS_FLOW = """\
## Performance Addon: Systems Languages

1. **Cache Hierarchy Impact:** Trace data access patterns through the hot path. \
Identify sequential vs random access to large arrays. Estimate working set \
size vs L1/L2/L3 cache sizes. Flag pointer-chasing patterns (linked lists, \
trees) that cause cache misses.

2. **System Call Overhead:** Map every system call (read, write, mmap, futex) \
in the hot path. Identify opportunities to batch syscalls (writev, \
io_uring, sendmmsg). Estimate kernel-user transition overhead and suggest \
buffering strategies.

3. **Compilation Unit Boundaries:** Identify hot-path function calls that \
cross translation unit boundaries and may not be inlined by the linker. \
Suggest LTO (Link-Time Optimisation) or header-only implementations \
for critical paths."""

# --- jvm (Java, Kotlin, Scala, Groovy) ------------------------------------

_PERF_ADDON_JVM_BUG = """\
## Performance Addon: JVM Languages

1. **GC Pressure & Object Churn:** Identify code that creates excessive \
short-lived objects: autoboxing primitives in loops (`Integer` vs `int`), \
string concatenation with `+` instead of `StringBuilder`, temporary \
collections created per iteration. Estimate young-gen allocation rate \
(MB/sec) and GC pause frequency.

2. **Object Pooling & Reuse Gaps:** Find expensive objects recreated per \
request: `DateTimeFormatter`, `Pattern`, `MessageDigest`, database \
connections, SSL contexts. These should be pooled, cached as statics, \
or created once per thread via `ThreadLocal`. Estimate allocation cost \
in microseconds.

3. **JIT Warmup & Deoptimisation:** Identify code patterns that prevent JIT \
compilation: megamorphic call sites (>2 receiver types), excessive use \
of reflection, dynamically generated classes. Look for methods that are \
too large for inlining (>35 bytecodes default) on critical paths.

4. **Stream Pipeline Inefficiency:** Find Java Streams that box primitives \
(use `IntStream`/`LongStream` instead), create unnecessary intermediate \
collections (`.collect()` followed by `.stream()`), or use `.parallel()` \
on small collections where fork-join overhead exceeds the benefit. Check \
for terminal operations that defeat laziness."""

_PERF_ADDON_JVM_DESIGN = """\
## Performance Addon: JVM Languages

1. **GC-Friendly Architecture:** Evaluate whether the design minimises old-gen \
promotion: are large caches using soft/weak references? Are long-lived \
objects pre-allocated during startup? Is the object graph shallow enough \
to avoid GC scanning overhead? Consider off-heap storage (DirectByteBuffer, \
Chronicle Map) for large datasets.

2. **Escape Analysis Awareness:** Assess whether hot-path objects are candidates \
for scalar replacement (escape analysis). Objects that escape the method \
(stored in fields, passed to other threads, returned) cannot be stack- \
allocated. Evaluate whether design changes could confine objects to method \
scope.

3. **Concurrency Model Fit:** Review whether the concurrency model matches the \
workload: virtual threads (Loom) for I/O-bound, ForkJoinPool for CPU-bound, \
reactive streams for backpressure. Check for `synchronized` blocks that \
should use `java.util.concurrent` constructs (StampedLock, ConcurrentHashMap, \
LongAdder)."""

_PERF_ADDON_JVM_STATIC = """\
## Performance Addon: JVM Languages

1. **Autoboxing in Hot Paths:** Scan for implicit boxing: `Map<Integer, ...>` \
accessed in loops, `List<Long>` vs `long[]` or `TLongArrayList`, generic \
methods receiving primitives. Each autobox allocates ~16 bytes. At 1M \
iterations this wastes ~16MB and triggers young-gen GC.

2. **String Handling Anti-Patterns:** Find `String.format()` in logging \
(use parameterised logging), `+` concatenation in loops (use \
`StringBuilder`), `String.split()` with regex that could use \
`StringTokenizer` or indexOf. Check for `toString()` called on \
objects only to parse them back.

3. **Collection Sizing & Type:** Identify `HashMap`/`ArrayList` created without \
initial capacity in loops processing known-size data. Find `LinkedList` \
used as a general-purpose list (poor cache locality). Flag `Hashtable` \
or `Vector` (synchronised overhead) where concurrent alternatives exist.

4. **Reflection & Proxy Overhead:** Find `Method.invoke()`, `Field.get()`, \
or `Proxy.newProxyInstance()` on hot paths. These bypass JIT optimisation \
and add microseconds per call. Suggest `MethodHandle`, `LambdaMetafactory`, \
or code generation as alternatives."""

_PERF_ADDON_JVM_FLOW = """\
## Performance Addon: JVM Languages

1. **GC Pause Points:** Trace the hot path and identify allocation-heavy stages \
that will trigger GC. Map young-gen vs old-gen allocation patterns. Estimate \
pause times based on heap size and GC algorithm (G1, ZGC, Shenandoah). \
Identify stages where GC pauses would violate latency budgets.

2. **JIT Compilation Boundaries:** Identify methods on the hot path that may \
not be JIT-compiled due to size, complexity, or polymorphism. Trace call \
sites to determine if they are monomorphic (fast), bimorphic, or \
megamorphic (slow virtual dispatch). Estimate the JIT warmup period \
in number of invocations.

3. **Thread Pool & Executor Flow:** Map how requests flow through executor \
services, fork-join pools, and completion stages. Identify blocking calls \
that consume thread pool threads. Estimate queue depths and thread \
utilisation under load. Flag unbounded queues that risk OOM."""

# --- dotnet (C#, F#, VB.NET) ---------------------------------------------

_PERF_ADDON_DOTNET_BUG = """\
## Performance Addon: .NET Languages

1. **ValueType vs ReferenceType Misuse:** Identify large structs (>16 bytes) \
passed by value causing excessive copying. Find classes that should be \
structs (small, immutable, short-lived). Look for boxing of value types \
in collections or interface calls. Check for `readonly struct` opportunities \
to avoid defensive copies.

2. **Span<T> & Memory<T> Opportunities:** Find `string.Substring()`, \
`Array.Copy()`, or `byte[]` slicing that could use `Span<T>` or \
`Memory<T>` to avoid allocation. Identify parsing code that creates \
intermediate strings instead of operating on `ReadOnlySpan<char>`. \
Estimate allocations saved per operation.

3. **Async Overhead & Task Allocation:** Find `async` methods that complete \
synchronously most of the time (should use `ValueTask<T>`). Look for \
`Task.Result` or `.Wait()` causing thread pool starvation. Identify \
unnecessary `async`/`await` on methods that just forward a single task. \
Check for `ConfigureAwait(false)` missing in library code.

4. **LINQ Materialisation & Allocation:** Find `.ToList()` or `.ToArray()` \
called on LINQ queries only to iterate once (remove materialisation). \
Identify multiple LINQ enumerations of the same query. Look for LINQ \
in tight loops where a manual loop avoids delegate and enumerator \
allocation."""

_PERF_ADDON_DOTNET_DESIGN = """\
## Performance Addon: .NET Languages

1. **ArrayPool & Object Pooling:** Evaluate whether frequently allocated \
arrays use `ArrayPool<T>.Shared` for reuse. Check for \
`ObjectPool<T>` usage for expensive objects (StringBuilder, \
HttpClient). Assess whether `RecyclableMemoryStream` replaces \
`MemoryStream` for large buffers.

2. **Struct Layout & Packing:** Review struct definitions for optimal \
memory layout. Use `[StructLayout(LayoutKind.Sequential)]` where \
interop or cache efficiency matters. Evaluate whether `LayoutKind.Auto` \
allows the runtime to reorder fields for better packing. Check alignment \
of frequently accessed fields.

3. **Source Generator Architecture:** Assess whether reflection-heavy patterns \
(serialisation, DI, mapping) could use source generators instead. Source \
generators eliminate runtime reflection overhead and enable trim-friendly \
AOT compilation. Evaluate System.Text.Json source generation, Mapperly, \
or AutoMapper source generation."""

_PERF_ADDON_DOTNET_STATIC = """\
## Performance Addon: .NET Languages

1. **String Allocation Patterns:** Find `string.Concat` in loops (use \
`StringBuilder` or `string.Create`), `string.Format` where interpolation \
suffices, `Encoding.GetString` creating intermediate strings when \
`Span`-based parsing would avoid allocation. Check for `string.ToLower()` \
in comparisons instead of `StringComparison.OrdinalIgnoreCase`.

2. **LINQ in Hot Paths:** Identify LINQ queries (`.Where()`, `.Select()`, \
`.Any()`) inside tight loops. Each LINQ call allocates an enumerator and \
delegate. For hot paths, manual `for`/`foreach` with pre-allocated \
collections avoids this overhead. Estimate allocation rate.

3. **Closure & Delegate Allocation:** Find lambda expressions that capture \
local variables (causes heap allocation of a display class). Identify \
delegates created per-call that could be cached as static fields. Look \
for `Func<>` and `Action<>` parameters on hot-path interfaces.

4. **Exception-Driven Control Flow:** Identify `try`/`catch` used for expected \
conditions (e.g., parsing with exception on failure instead of `TryParse`). \
Exception throwing is ~10 000x slower than a boolean return. Flag \
catch-and-rethrow patterns that add stack trace overhead."""

_PERF_ADDON_DOTNET_FLOW = """\
## Performance Addon: .NET Languages

1. **Async State Machine Overhead:** Trace async call chains and count the \
number of async state machines allocated per request. Identify methods \
with a single await that could be elided. Map where `ValueTask` would \
eliminate `Task` allocation on the synchronous fast path.

2. **GC Generation Flow:** Trace object lifetimes through the request path. \
Identify objects that survive Gen0 collection and promote to Gen1/Gen2 \
(long-lived caches, event handlers). Estimate Gen0/Gen1/Gen2 collection \
frequency under load. Flag pinned objects that fragment the heap.

3. **Thread Pool Utilisation:** Map how async operations interact with the \
.NET thread pool. Identify synchronous waits (`.Result`, `.Wait()`) that \
block thread pool threads. Estimate thread pool starvation risk under \
concurrent load. Check `ThreadPool.SetMinThreads` configuration."""

# --- go -------------------------------------------------------------------

_PERF_ADDON_GO_BUG = """\
## Performance Addon: Go

1. **Goroutine Scheduling Overhead:** Identify goroutine-per-item patterns \
where the overhead of goroutine creation and scheduling exceeds the work \
performed. Look for unbounded `go func()` launches without a worker pool \
(`errgroup`, `semaphore`). Estimate goroutine count under peak load and \
check for goroutine leaks (blocking on abandoned channels).

2. **Channel Buffer Sizing:** Find unbuffered channels used in producer-consumer \
patterns causing unnecessary synchronisation. Identify buffered channels \
with arbitrary sizes (magic numbers) that may overflow or underflow. \
Check for `select` statements with no `default` case causing goroutine \
parks. Estimate optimal buffer size based on throughput analysis.

3. **Escape Analysis Failures:** Identify variables that escape to the heap \
unnecessarily: returning pointers to local variables, storing locals in \
interface values, closures capturing loop variables. Use `go build \
-gcflags='-m'` output mentally to predict escape decisions. Suggest \
value receivers, pre-allocated slices, and sync.Pool to reduce GC load.

4. **Slice & Map Pre-Allocation:** Find `append()` calls in loops without \
`make([]T, 0, expectedCap)`. Identify maps created with default size \
that grow repeatedly. Each growth copies the backing array. Estimate \
wasted allocations and suggest `make()` with capacity hints."""

_PERF_ADDON_GO_DESIGN = """\
## Performance Addon: Go

1. **sync.Pool & Object Reuse:** Evaluate whether frequently allocated objects \
(buffers, request structs, encoders) use `sync.Pool` for reuse across \
GC cycles. Check that pooled objects are properly reset before returning \
to the pool. Assess whether pool usage patterns survive GC (pools are \
cleared every GC cycle).

2. **pprof-Ready Architecture:** Review whether the application exposes \
`net/http/pprof` endpoints. Check for meaningful labels in CPU and \
memory profiles. Evaluate whether hot-path functions are structured \
for easy profiling (not too deeply nested, not inlined away). Assess \
tracing instrumentation via `runtime/trace`.

3. **Interface vs Concrete Type Trade-Offs:** Identify interface parameters \
on hot paths that prevent inlining and cause heap allocation (interface \
boxing). Evaluate whether generic functions (Go 1.18+) would enable \
monomorphisation. Check for `interface{}` / `any` used where a concrete \
type or type constraint would enable optimisation."""

_PERF_ADDON_GO_STATIC = """\
## Performance Addon: Go

1. **String & Byte Slice Conversion:** Find `string([]byte)` and \
`[]byte(string)` conversions in loops — each allocates a copy. Use \
`unsafe.String` / `unsafe.Slice` where lifetime is guaranteed, or \
restructure to work on `[]byte` throughout. Identify `fmt.Sprintf` \
used for simple concatenation where `strings.Builder` suffices.

2. **Deferred Function Overhead:** Find `defer` statements inside tight \
loops — each defer allocates a closure on the heap. Refactor to call \
the function directly or move the loop body to a separate function \
where defer executes once per call. Estimate overhead per iteration.

3. **Map Iteration Non-Determinism:** While not a performance bug per se, \
identify code that sorts map keys every iteration. Suggest maintaining \
a separate sorted slice or using a `btree` for ordered iteration. Flag \
maps used as sets where a `struct{}` value type saves memory.

4. **Reflection in Hot Paths:** Find `reflect.ValueOf`, `reflect.TypeOf`, \
or `encoding/json.Marshal` (uses reflection) in request-handling loops. \
Suggest code generation (`easyjson`, `go-codec`) or manual \
marshal/unmarshal for hot paths. Estimate per-call overhead (~1us \
for reflection vs ~100ns for generated code)."""

_PERF_ADDON_GO_FLOW = """\
## Performance Addon: Go

1. **Goroutine Lifecycle Mapping:** Trace goroutine creation, communication \
(channels, mutexes), and termination through the hot path. Identify \
goroutines that outlive their usefulness (leak). Map the concurrency \
fan-out and fan-in pattern. Estimate peak goroutine count and scheduler \
overhead.

2. **GC Impact on Latency:** Map heap allocation points along the hot path. \
Estimate the allocation rate (MB/sec) and predict GC frequency. Identify \
stages where GC pauses (even sub-millisecond with Go 1.19+) would \
compound with I/O latency. Suggest allocation-free alternatives for \
the most impactful sites.

3. **Channel Synchronisation Overhead:** Trace data flow through channels. \
Identify serial bottlenecks where a single channel forces sequential \
processing. Map buffered vs unbuffered channel usage and estimate \
the time goroutines spend blocked on channel operations."""

# --- frontend (JavaScript, TypeScript, CSS/HTML) --------------------------

_PERF_ADDON_FRONTEND_BUG = """\
## Performance Addon: Frontend

1. **Bundle Size & Tree-Shaking Failures:** Identify imports that pull in \
entire libraries when only a single function is needed (e.g., \
`import _ from 'lodash'` vs `import debounce from 'lodash/debounce'`). \
Look for barrel files (`index.ts` re-exports) that defeat tree-shaking. \
Check for dynamic `require()` preventing dead-code elimination. Estimate \
bundle size impact in KB (gzipped).

2. **Render-Blocking & Layout Thrashing:** Find DOM reads (offsetHeight, \
getBoundingClientRect) interleaved with DOM writes causing forced \
synchronous layout. Identify CSS/JS in `<head>` without `async`/`defer` \
blocking first paint. Look for large component re-renders triggered by \
state changes in parent components. Estimate frames dropped or CLS impact.

3. **Virtual DOM Reconciliation Overhead:** Find React/Vue components that \
re-render unnecessarily: missing `React.memo`, `useMemo`, `useCallback`, \
or Vue `computed`. Identify list rendering without stable `key` props \
causing full list re-creation. Look for inline object/array literals \
in JSX props that create new references every render.

4. **Memory Leaks in SPAs:** Identify event listeners added in \
`useEffect`/`mounted` without cleanup. Find `setInterval`/`setTimeout` \
references not cleared on unmount. Look for closures in module scope \
capturing component state. Check for growing `Map`/`Set` caches without \
eviction in long-running SPA sessions."""

_PERF_ADDON_FRONTEND_DESIGN = """\
## Performance Addon: Frontend

1. **Code Splitting & Lazy Loading Architecture:** Evaluate whether routes \
and heavy components use dynamic `import()` for code splitting. Check \
for appropriate Suspense boundaries. Assess whether the initial bundle \
includes only above-the-fold content. Review prefetch/preload strategies \
for likely next navigations.

2. **Web Worker Offloading:** Identify CPU-intensive operations (parsing, \
sorting, encryption, image processing) running on the main thread. \
Evaluate whether they can be offloaded to Web Workers or \
`OffscreenCanvas`. Assess whether `SharedArrayBuffer` and `Atomics` \
could enable zero-copy communication.

3. **Rendering Strategy Selection:** Evaluate whether the application uses \
the right rendering strategy: SSR for SEO/first-paint, SSG for static \
content, CSR for interactive dashboards, ISR for semi-dynamic pages. \
Check for hydration mismatches that cause full client re-renders."""

_PERF_ADDON_FRONTEND_STATIC = """\
## Performance Addon: Frontend

1. **requestAnimationFrame Misuse:** Find `setInterval`/`setTimeout` used \
for animations instead of `requestAnimationFrame`. Identify rAF callbacks \
that perform heavy computation (should be split across frames). Look for \
missing `cancelAnimationFrame` on cleanup paths. Flag CSS properties \
animated via JavaScript that could use CSS transitions/animations.

2. **Event Handler Overhead:** Find event listeners on individual list items \
instead of delegated handlers on the parent. Identify scroll/resize \
handlers without debouncing or throttling. Look for `addEventListener` \
with `{passive: false}` blocking scroll on touch events. Check for \
`preventDefault()` called unnecessarily.

3. **Image & Asset Optimisation Gaps:** Find `<img>` tags without `loading="lazy"`, \
missing `width`/`height` attributes causing layout shift, unoptimised \
formats (PNG where WebP/AVIF would reduce size 50-80%). Identify large \
JSON payloads that could use pagination or streaming. Flag base64-encoded \
assets in CSS that bloat the stylesheet.

4. **Module Loading Patterns:** Identify synchronous `require()` in browser \
bundles, circular dependencies that cause initialisation issues, and \
barrel files that import everything. Check for `sideEffects: false` in \
package.json to enable tree-shaking. Flag polyfills included for browsers \
no longer supported."""

_PERF_ADDON_FRONTEND_FLOW = """\
## Performance Addon: Frontend

1. **Critical Rendering Path:** Trace the browser rendering pipeline from \
navigation to first meaningful paint. Identify render-blocking resources \
(CSS in head, synchronous JS). Map the order of network requests, parsing, \
style calculation, layout, paint, and composite. Estimate Time to First \
Byte (TTFB), First Contentful Paint (FCP), and Largest Contentful Paint (LCP).

2. **State Update Propagation:** Trace how a state change propagates through \
the component tree. Identify which components re-render and whether the \
re-renders are necessary. Map the dependency graph of reactive state \
(Redux selectors, Vue computed, React context). Estimate wasted renders \
per user interaction.

3. **Network Waterfall Analysis:** Map the sequence of API calls, asset loads, \
and third-party scripts. Identify serial request chains that could be \
parallelised. Flag requests that block rendering. Estimate total waterfall \
duration and identify the critical chain."""

# --- functional (Haskell, Erlang/Elixir, OCaml, Clojure, Scala FP) -------

_PERF_ADDON_FUNCTIONAL_BUG = """\
## Performance Addon: Functional Languages

1. **Tail Call Optimisation Failures:** Identify recursive functions that are \
not tail-recursive and will blow the stack on large inputs. Look for \
accidental non-tail calls: operations after the recursive call (e.g., \
`1 + f(n-1)` instead of accumulator passing). Check whether the runtime \
actually optimises tail calls (Erlang/Elixir: yes, Clojure: requires \
`recur`, Scala: `@tailrec` annotation).

2. **Lazy Evaluation Thunk Leaks:** In Haskell or lazy Scala, find thunks \
that accumulate without being forced, causing space leaks. Look for \
`foldl` (strict `foldl'` is usually correct), lazy accumulators in \
recursive functions, and `Data.Map.Lazy` where `Data.Map.Strict` is \
appropriate. Estimate heap growth rate from unfocred thunks.

3. **Persistent Data Structure Overhead:** Identify operations on immutable \
data structures where the structural sharing overhead exceeds the cost \
of a mutable alternative. Look for frequent random updates on large \
vectors (O(log n) per update vs O(1) mutable). Evaluate whether \
transient/mutable builders are available and should be used.

4. **Fusion & Deforestation Gaps:** Find chains of list operations that \
create intermediate lists: `map f . filter p . map g`. Check whether \
the runtime/compiler applies stream fusion (GHC) or transducers \
(Clojure). Identify cases where manual fusion or `foldr`/`build` \
rewriting would eliminate intermediate allocations."""

_PERF_ADDON_FUNCTIONAL_DESIGN = """\
## Performance Addon: Functional Languages

1. **Strictness Architecture:** Evaluate whether the application correctly \
manages strict vs lazy evaluation boundaries. In Haskell, check for \
`BangPatterns`, `StrictData`, and `NFData` constraints where accumulation \
occurs. In Clojure, assess use of `doall`/`dorun` to force lazy sequences \
before crossing I/O boundaries. Design lazy pipelines that stream but \
force at consumption points.

2. **Process/Actor Model Scaling:** For Erlang/Elixir, evaluate the actor \
architecture: process-per-connection vs pooled workers, mailbox overflow \
risk, supervision tree design. Check for processes holding large state \
that increases GC per-process. Assess whether ETS tables are used for \
shared read-heavy data to avoid message-passing overhead.

3. **Algebraic Effect Management:** Evaluate whether effect systems (IO monad, \
ZIO, Cats Effect) are structured for performance: resource brackets for \
cleanup, concurrent effect composition (`parTraverse`, `Task.parSequence`), \
and appropriate fiber/green-thread usage. Check for unnecessary effect \
wrapping on pure computations."""

_PERF_ADDON_FUNCTIONAL_STATIC = """\
## Performance Addon: Functional Languages

1. **Unnecessary Immutable Copies:** Find repeated `copy()` or `updated()` \
calls on large collections in loops. In Scala, identify `case class` \
`.copy()` chains that could use a builder. In Clojure, look for `assoc` \
chains on maps that could use `transient`. Estimate allocation overhead \
per iteration.

2. **Pattern Matching Complexity:** Identify deeply nested pattern matches \
that may cause exponential compilation time or poor runtime dispatch. \
Look for overlapping patterns that the compiler cannot optimise. In \
Erlang/Elixir, check for function clause ordering that puts rare cases \
first (most common should be first for faster matching).

3. **Monadic Overhead in Hot Paths:** Find monadic bind chains (`>>=`, \
`flatMap`, `for`-comprehensions) in tight loops where the monad overhead \
(allocation of closures, trampolining) dominates. Evaluate whether \
`unsafePerformIO` (Haskell), `unsafeRun` (ZIO), or imperative local \
mutation is justified for performance-critical sections.

4. **Higher-Order Function Allocation:** Identify closures created per-element \
in map/filter/fold chains. In JVM-based functional languages (Scala, \
Clojure), each closure is a small object allocation. Suggest function \
objects as named vals/defs or method references to enable reuse."""

_PERF_ADDON_FUNCTIONAL_FLOW = """\
## Performance Addon: Functional Languages

1. **Lazy Evaluation Execution Order:** Trace the actual evaluation order \
of lazy expressions. Identify where forcing a value triggers a cascade \
of thunk evaluations. Map the "demand propagation" through the call graph. \
Estimate peak memory from accumulated thunks before forcing.

2. **Message-Passing Topology:** For actor-based systems, trace message flow \
between processes/actors. Identify hot-spot actors that receive \
disproportionate traffic. Map mailbox queue depths under load. Estimate \
message serialisation/deserialisation cost for cross-node communication.

3. **Effect Composition Pipeline:** Trace how effects (IO, Task, Future) \
compose through `flatMap`/`bind` chains. Identify sequential effect \
chains that could be parallelised (`parTraverse`, `mapN`). Map \
resource acquisition and release points. Estimate overhead of effect \
runtime (fiber scheduling, trampolining) vs direct execution."""

# --- infrastructure (Bash, PowerShell, Dockerfile, YAML/CI) ---------------

_PERF_ADDON_INFRA_BUG = """\
## Performance Addon: Infrastructure Scripts

1. **Script Startup & Process Spawning:** Identify commands that spawn \
subprocesses unnecessarily: `cat file | grep` (use `grep file` directly), \
`echo $(command)` (use `command` directly), `for f in $(find ...)` (use \
`find -exec` or `xargs`). Each subprocess fork costs ~2-5ms and adds up \
in loops. Estimate total fork overhead.

2. **I/O Redirection Inefficiency:** Find repeated file opens in loops \
(redirect inside loop vs redirect the entire loop). Identify `>>` \
appends that could be a single `>` with collected output. Look for \
`read` line-by-line patterns that should use `awk` or `sed` for bulk \
processing. Estimate I/O syscall reduction.

3. **Docker Layer & Cache Invalidation:** Identify Dockerfile instructions \
ordered to maximise cache invalidation: `COPY . .` before `RUN pip \
install` (should copy requirements first). Find multi-stage builds \
missing `--from` to copy only artifacts. Look for large base images \
where alpine or distroless would reduce pull/startup time. Estimate \
layer cache hit rate.

4. **CI/CD Pipeline Parallelism Gaps:** Find sequential CI steps that could \
run in parallel (lint + test + build). Identify missing caching of \
dependencies (`node_modules`, `.pip`, `.m2`). Look for jobs that \
download the same artifacts repeatedly. Estimate pipeline duration \
reduction from parallelisation and caching."""

_PERF_ADDON_INFRA_DESIGN = """\
## Performance Addon: Infrastructure Scripts

1. **Caching Strategy in CI/CD:** Evaluate dependency caching: are lock files \
used as cache keys? Is the cache scoped correctly (per-branch, per-PR, \
global)? Check for layer caching in Docker builds (BuildKit cache mounts, \
`--mount=type=cache`). Assess whether build artifacts are cached between \
stages.

2. **Parallel Execution Architecture:** Review whether the CI pipeline uses \
matrix strategies, parallel test shards, or fan-out/fan-in patterns. \
Evaluate whether the job dependency graph is optimal or has unnecessary \
serial bottlenecks. Check for `needs:` / `depends_on:` constraints \
that could be relaxed.

3. **Image & Artifact Size Optimisation:** Evaluate base image selection \
(full OS vs slim vs alpine vs distroless vs scratch). Check for \
multi-stage builds that discard build tools. Assess whether `.dockerignore` \
excludes test files, docs, and local config. Estimate image size reduction \
from each optimisation."""

_PERF_ADDON_INFRA_STATIC = """\
## Performance Addon: Infrastructure Scripts

1. **Useless Use of Cat & Pipe Chains:** Find `cat file | cmd` where `cmd file` \
or `cmd < file` suffices. Identify long pipe chains where a single `awk` \
command could replace `grep | cut | sort | uniq`. Each pipe creates a \
subprocess and kernel buffers. Estimate subprocess count reduction.

2. **Shell Loop Anti-Patterns:** Find `for line in $(cat file)` which breaks \
on whitespace and loads the entire file into memory. Identify `while read` \
loops calling external commands per line instead of using built-in string \
operations. Look for `expr` or `bc` for arithmetic that `$(( ))` handles \
natively.

3. **YAML Anchors & Template Reuse:** In CI/CD configs, find duplicated step \
definitions that could use YAML anchors (`&`/`*`) or template includes \
(`extends`, `!reference`). Identify repeated `apt-get install` or `pip \
install` blocks across jobs that could be in a shared base image.

4. **Dockerfile Instruction Ordering:** Check that instructions are ordered \
from least-frequently-changed to most-frequently-changed. Find `RUN` \
instructions that could be combined to reduce layers. Identify `ENV` or \
`ARG` that invalidate cache unnecessarily when changed. Flag `ADD` used \
where `COPY` suffices (ADD has extra features that prevent caching)."""

_PERF_ADDON_INFRA_FLOW = """\
## Performance Addon: Infrastructure Scripts

1. **Pipeline Critical Path:** Trace the CI/CD pipeline from trigger to \
deployment. Identify the longest sequential chain of jobs (critical path). \
Map which jobs can run in parallel. Estimate total pipeline duration and \
theoretical minimum with full parallelisation.

2. **Container Startup Sequence:** Trace the container lifecycle: pull, create, \
start, health check, ready. Identify slow startup causes: large image pull, \
slow entrypoint scripts, health check polling intervals. Estimate time \
from deployment trigger to first request served.

3. **Dependency Resolution Flow:** Trace how dependencies are resolved and \
installed. Map cache hits vs cold installs. Identify duplicate dependency \
resolution across jobs or stages. Estimate time spent on dependency \
management as a percentage of total pipeline duration."""


# ---------------------------------------------------------------------------
# Exported collections
# ---------------------------------------------------------------------------

PERFORMANCE_TEMPLATES: list[PromptTemplate] = [
    _t("bug_analysis",
       "Find performance bugs: complexity, leaks, I/O bottlenecks, N+1, concurrency",
       _PERF_BUG),
    _t("code_design",
       "Evaluate design for scalability, caching, pooling, lazy loading, batching",
       _PERF_DESIGN),
    _t("code_flow",
       "Trace hot paths, map I/O boundaries, identify parallelisation opportunities",
       _PERF_FLOW),
    _t("mermaid",
       "Generate performance diagrams: hot paths, bottlenecks, capacity planning",
       _PERF_MERMAID),
    _t("requirement",
       "Extract SLAs, throughput targets, latency budgets, scaling requirements",
       _PERF_REQUIREMENT),
    _t("static_analysis",
       "Detect anti-patterns: quadratic loops, copies, blocking, missing indices",
       _PERF_STATIC),
    _t("comment_generator",
       "Write performance-focused PR comments with impact estimates",
       _PERF_COMMENT),
    _t("commit_analysis",
       "Analyse commits for performance impact: deps, algorithms, migrations",
       _PERF_COMMIT),
]

# Addons indexed by (family, agent) — merged with universal at apply time
PERFORMANCE_ADDONS: dict[tuple[str, str], str] = {
    # dynamic_scripting
    ("dynamic_scripting", "bug_analysis"):    _PERF_ADDON_DYNAMIC_BUG,
    ("dynamic_scripting", "code_design"):     _PERF_ADDON_DYNAMIC_DESIGN,
    ("dynamic_scripting", "static_analysis"): _PERF_ADDON_DYNAMIC_STATIC,
    ("dynamic_scripting", "code_flow"):       _PERF_ADDON_DYNAMIC_FLOW,
    # systems
    ("systems", "bug_analysis"):    _PERF_ADDON_SYSTEMS_BUG,
    ("systems", "code_design"):     _PERF_ADDON_SYSTEMS_DESIGN,
    ("systems", "static_analysis"): _PERF_ADDON_SYSTEMS_STATIC,
    ("systems", "code_flow"):       _PERF_ADDON_SYSTEMS_FLOW,
    # jvm
    ("jvm", "bug_analysis"):    _PERF_ADDON_JVM_BUG,
    ("jvm", "code_design"):     _PERF_ADDON_JVM_DESIGN,
    ("jvm", "static_analysis"): _PERF_ADDON_JVM_STATIC,
    ("jvm", "code_flow"):       _PERF_ADDON_JVM_FLOW,
    # dotnet
    ("dotnet", "bug_analysis"):    _PERF_ADDON_DOTNET_BUG,
    ("dotnet", "code_design"):     _PERF_ADDON_DOTNET_DESIGN,
    ("dotnet", "static_analysis"): _PERF_ADDON_DOTNET_STATIC,
    ("dotnet", "code_flow"):       _PERF_ADDON_DOTNET_FLOW,
    # go
    ("go", "bug_analysis"):    _PERF_ADDON_GO_BUG,
    ("go", "code_design"):     _PERF_ADDON_GO_DESIGN,
    ("go", "static_analysis"): _PERF_ADDON_GO_STATIC,
    ("go", "code_flow"):       _PERF_ADDON_GO_FLOW,
    # frontend
    ("frontend", "bug_analysis"):    _PERF_ADDON_FRONTEND_BUG,
    ("frontend", "code_design"):     _PERF_ADDON_FRONTEND_DESIGN,
    ("frontend", "static_analysis"): _PERF_ADDON_FRONTEND_STATIC,
    ("frontend", "code_flow"):       _PERF_ADDON_FRONTEND_FLOW,
    # functional
    ("functional", "bug_analysis"):    _PERF_ADDON_FUNCTIONAL_BUG,
    ("functional", "code_design"):     _PERF_ADDON_FUNCTIONAL_DESIGN,
    ("functional", "static_analysis"): _PERF_ADDON_FUNCTIONAL_STATIC,
    ("functional", "code_flow"):       _PERF_ADDON_FUNCTIONAL_FLOW,
    # infrastructure
    ("infrastructure", "bug_analysis"):    _PERF_ADDON_INFRA_BUG,
    ("infrastructure", "code_design"):     _PERF_ADDON_INFRA_DESIGN,
    ("infrastructure", "static_analysis"): _PERF_ADDON_INFRA_STATIC,
    ("infrastructure", "code_flow"):       _PERF_ADDON_INFRA_FLOW,
}
