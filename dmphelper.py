from diff_match_patch import diff_match_patch
dmp = diff_match_patch()

def diff(text1, text2):
	return dmp.patch_toText(dmp.patch_make(text1, text2))

def patch(origtext, diff):
	return dmp.patch_apply(dmp.patch_fromText(diff),origtext)[0]
