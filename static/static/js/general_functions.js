function veracity_test(user_points, MINIMUM_POINTS_FOR_POSTING_IMAGES) {
	if (user_points < MINIMUM_POINTS_FOR_POSTING_IMAGES) {
		alert('Você precisa de pelo menos ' + MINIMUM_POINTS_FOR_POSTING_IMAGES + ' pontos para postar imagens.');
		return false;
	}
	return true;
}
