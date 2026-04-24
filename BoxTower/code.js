const field = document.getElementById('game-field');
const blockSize = 40;
let lastBlock = null;
let allElements = [];
let isGameOver = false;

field.onclick = function(event){
	if(isGameOver){
		return;
	}
	let x = event.offsetX - (blockSize / 2);
	let y = event.offsetY - (blockSize / 2);

	const newBlock = document.createElement('div');
	newBlock.classList.add('block');
	newBlock.style.left = x + 'px';
	newBlock.style.top = y + 'px';
	newBlock.style.background = `hsl(${Math.random() *360}, 70%, 60%)`;
	field.appendChild(newBlock);
	allElements.push(newBlock);

	//логіка першого блока

	if (!lastBlock) {
		let finalY = 460;
		setTimeout(() =>{
			newBlock.style.top = finalY + 'px';
			lastBlock = {x: x, y: finalY };
		},50);
		return;
	}

	//логіка наступних блоків

	let targetY = lastBlock.y - blockSize;
	const centerX = x + (blockSize / 2);
	const onBalance = (centerX > lastBlock.x) && (centerX < lastBlock.x + blockSize);
	if (onBalance) {
		setTimeout(() => {
			newBlock.style.top = targetY + 'px';
			lastBlock = {x: x, y: targetY};
			if (targetY <= 0) {
				alert("Win 67");
				location.reload();

			}
		},50);
	}
	else {
		isGameOver = true;
		setTimeout(() => {
			newBlock.style.top = (y + 100) + 'px';
			newBlock.style.transform = "rotate(90deg)";

			 setTimeout(() => {
			 	allElements.forEach((el,index) => {
			 		setTimeout(() => {
			 			el.classList.add('collapse');

			 		}, index * 50);
			 	});
			 	setTimeout(() => {
			 		alert("THE TOWER HAS COLLAPSED ! Try again.");
			 		location.reload();
			 	}, allElements.length * 50 + 500);
			 },300);
		},50);
	}


};