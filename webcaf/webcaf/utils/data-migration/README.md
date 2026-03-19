# Migrating old webcaf data into new format

## Usage

First you will need to copy the required files to the relevant folders.

Copy the following files from the production govassure s3 bucket:

- assessments-combined/cos-igps/all.gz -> [data/assessments-combined/cos-igps/](data/assessments-combined/cos-igps/)

This contains the combined COS and IGPS assessments.

- assessments-combined/overview/all.gz -> [data/assessments-combined/overview/](data/assessments-combined/overview/)

This contains the metadata about the assessments

- assessment-definitions/*.gz -> [data/assessment-definitions/](data/assessment-definitions/)

This contains the assessment definitions

- hashed_ids/*.gz -> [data/hashed_ids/](data/hashed_ids/)

This contains information on the systems, organisations and their associated assessments

Run the following command to carry out the transformation
The results will be stored in the [data/transformed/](data/transformed/) folder.
```bash
    python transform.py
```
