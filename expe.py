from clinicaio import query
from clinicaio.dataset import *
from clinicaio.query import *

# IN _env.py:
#
# from pathlib import Path
# test_bids_read_path=Path("/path/to/BIDS")
from _env import test_bids_read_path

dataset = BIDSDataset.populate_from_dir(bids_dir=test_bids_read_path, sessions_info=False)
#print(dataset)

print(dataset._bids_path)
print(dataset.description)
for subject in dataset._subjects.values():
	print(subject.id)
	for session in subject.sessions.values():
		print("\t", session.id)#, session.info)
		for data_type, images in session._images.items():
			print(f"\t\t{data_type}")
			for image in images:
				print(f"\t\t\t{image}")




image_query = ImageQuery(
	subjects=["sub-ADNI027S0074"], 
	sessions=["ses-M000"], 
	data_type=DataType.PET,
	entities={"trc": "18FFDG", "rec": "coregiso8"},
	suffix="pet",
)
for found_image in image_query.query(dataset):
	nifti_path = dataset.get_nifti_image_path(found_image)
	print(nifti_path)
	assert(os.path.exists(nifti_path))













def title(text: str):
	green="\033[38;2;80;200;120m"
	reset="\033[0m"
	print()
	print(f"{green}=============={text}=============={reset}")

################### Give me all tsv files
title("TSV files")
subjects_info = [subject.info for subject in dataset.all_subjects()]
print(subjects_info)
sessions_info = [session.info for subject, session in dataset.all_sessions()]
print(sessions_info)
scans_info = [image.scan_info for subject, session, data_type, image in dataset.all_images()]
print(scans_info)

################### Give me all images with this tracer (ex 18FFDG)
title("All images with a particular tracer")
query_results = ImageQuery(entities={"trc": "18FFDG"}).query(dataset)
#dataset.query_images(ImageQuery(entities={"trc": "18FFDG"}))
# p.ex
for query_result in query_results:
	image = query_result.image
	print(dataset.get_nifti_image_path(query_result), image)

################### Give me all T1w images paths
title("All T1w images paths")
t1w_paths = [dataset.get_nifti_image_path(query_result) for query_result in ImageQuery(suffix="T1w").query(dataset)]
#dataset.query_paths(ImageQuery(suffix="T1w"))
print(t1w_paths)

################### Give me all modalities for this one subject
subject_id = SubjectId("sub-ADNI027S0074")
title(f"All modalities for subject {subject_id}")
subject = dataset.subject_by_id(subject_id)
assert(subject is not None)
modalities = set(image.suffix for _,_,image in subject.all_images())
print(modalities)
# ou sinon
modalities = set(res.image.suffix for res in ImageQuery(subjects=[subject_id]).query(dataset))
print(modalities)

################### Give me all sessions for this one subject
title(f"All sessions for subject {subject_id}")
sessions_for_subject = subject.all_sessions()
print(sessions_for_subject)

################### Give me all subjects/sessions that have both a T1 and a PET image for the same session
title("All subjects/sessions that have both T1 and PET image for the same session")
def has_t1_and_pet(session: Session):
	if session.id.__str__() == "ses-M054":
		print("SESSION ", session)
	has_t1 = any(image.suffix == Suffix("T1w") for data_type, image in session.all_images())
	
	return has_t1 and any(data_type == DataType.PET for data_type, image in session.all_images())

subjects_and_sessions_with_t1_and_pet = filter(
	lambda v: has_t1_and_pet(v[1]),
	dataset.all_sessions(),
)
for subject, session in subjects_and_sessions_with_t1_and_pet:
	print("\t", subject.id, ":", "\n\t\t", session, "\n")

################### Give me the subjects that have more than one session
title("All subjects that have more than one session")
subjects_more_than_1_session = filter(lambda subject: subject.sessions_count() > 1, dataset.all_subjects())
for subject in subjects_more_than_1_session:
	print("\t", subject, "\n")

################### Check that all subjects/sessions have FLAIR images
title("All subjects/sessions have FLAIR images?")
def session_has_flair_image(session: Session):
	any(image.suffix == Suffix("FLAIR") for data_type, image in session.all_images())

sessions_all_have_flair = all(session_has_flair_image(session) for _, session in dataset.all_sessions())
print(sessions_all_have_flair)




################### Give me all the modalities available for each subject for this list of subjects
title("all modalities for each subject for a list of subjects")
subjects = dataset.all_subjects()
all_modalities_per_subject = [(
	set(
		image.suffix
		for session, data_type, image in subject.all_images()
	),
	subject,
) for subject in subjects]
for modalities, subject in all_modalities_per_subject:
	print("\t", modalities, "\n\t\t", subject, "\n")

################### Give me all the modalities available for all subjects for this list of subjects
title("all modalities for all subjects")
subject=None
all_modalities_for_subjects = set(
	image.suffix
	for subject in dataset.all_subjects()
	for session, data_type, image in subject.all_images()
)
print(all_modalities_for_subjects)

################### Can you tell me if all subjects have only one session
title("all subjects have only one session?")
all_subjects_have_one_session = all(len(subject.sessions) == 1 for subject in dataset.all_subjects())
print(all_subjects_have_one_session)