function shuffle() {
  var container = document.getElementById('reslist');
  var elementsArray = Array.prototype.slice.call(container.getElementsByClassName('sres'));
	elementsArray.forEach(function(element){
	container.removeChild(element);
  })
  shuffleArray(elementsArray);
  elementsArray.forEach(function(element){
  container.appendChild(element);
})
}

function shuffleArray(array) {
	for (var i = 20; i < array.length; i++) {
		var chance = Math.floor(Math.random() * (i-15));
		if (chance < 5) {
			var j = Math.floor(Math.random() * (i-15));
			var temp = array[i];
			array.splice(i, 1);
			array.splice(j, 0, temp);
		}
	}
	return array;
}
shuffle();
