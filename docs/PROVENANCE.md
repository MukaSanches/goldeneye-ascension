# Provenance and integration policy

Ascension preserves the Git history, authorship, licenses and notices inherited from the projects on which the codebase was built. Independence means independent governance and engineering decisions; it does not mean claiming inherited work as original Ascension work.

## Rules for imported work

Before integrating code or assets from another project, record when practical:

- source project and canonical location;
- author/commit/PR or issue that identifies the work;
- applicable license;
- Ascension files/subsystems affected;
- whether the implementation is REUSE, ADAPT, LEARN or AVOID;
- compatibility and regression risks;
- tests required and tests actually performed.

## Proprietary content

Do not commit commercial ROM images or proprietary game assets merely to make a build self-contained. Keep extraction/build workflows separate from redistributable source code.

## Validation

A successful compile is necessary but not sufficient for functional changes. Rendering requires visual validation, input requires control-feel validation, and mission/gameplay changes require relevant gameplay regression testing.

## Reversibility

Ascension changes should be grouped into coherent commits. Major migrations should have an explicit backup branch or known commit so a regression can be reverted without discarding unrelated work.

## External upstreams

External repositories are monitored as sources of engineering knowledge and candidate fixes. Ascension does not automatically fast-forward its main branch to an external main branch. A candidate change is independently reviewed and integrated only when it benefits Ascension.
