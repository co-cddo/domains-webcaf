# YAML Representation of CAF

`cyber-assessment-framework-v3.2.yaml` a YAML representation of the 3.2 CAF from the [NCSC PDF version](https://www.ncsc.gov.uk/static-assets/documents/cyber-assessment-framework-v3.2.pdf).

## Structure

The YAML reflects the hierarchy of concepts in the CAF: Objectives, which have Principles, which have 'Sections' (the CAF doesn't seem to give these a name), which have Indicators. Indicators are grouped under 'Achieved', 'Not Achieved' etc.

Each of Objectives, Principles, Sections and Indicators has its own index.

## Testing

`tests/test_yaml.py` tests that the indexes (objectives, principles, sections, indicators) are unique. It cannot catch duplicate indexes (i.e. two indicators with index `A1.a.1`) when these happen in the same YAML dictionary (e.g. the duplicates are both under the same 'Achieved' heading) because the second just overwrites the first when the YAML is parsed.

The `check-yaml` pre-commit hook *will* catch duplicate index values in the same dictionary but *will not* catch them when they're spread across multiple dictionaries because this is perfectly valid YAML (duplicate keys in a YAML dictionary is strictly speaking valid, but in practice almost always a sign of an error so the hook catches it).

To test changes to the YAML file it is therefore important to run the following from the project root:

```
python -m unittest tests.test_yaml
pre-commit run check-yaml --files frameworks/cyber-assessment-framework-v3.2.yaml
```

## create-schema.py

The script does *most* of the work involved in creating a YAML representation of the CAF from the PDF.

Comments in the script refer to some limitations to the degree of automation possible, the biggest being that the parser could not sort the indicators under 'Achieved', 'Not achieved' etc and this had to be done manually. There were other problems with matching indictors, e.g. when they spanned two pages, which became apparent later, needing further manual work.

In hindsight it would probably have been quicker to scrape the web version, even though it's spread across several pages which would somehow have to be stitched together.

The script could be improved in many, many ways but was of no use once manual editing began and is kept just for reference.


## caf32-reindex.py

Used to re-index the indicators, repacing the global, numerical index with one based on each indicator's position in the nested structure such that `1` became `A1.a.1`.

We may need to create new, additional indexes on the indicators corresponding to those in subsequent CAF versions, in which case this script might act as a basis.
