/*
Modal popup for EPUB3 front-matter (fm) pages
Vanilla JavaScript
Author: Bo Krantz Simonsen, 2024, boks@kb.dk
License:  CC0 (public domain)
*/

function toc() {
	showModal('tocModal');
}


function showModal(id) {
	var closeFunc = function(id) {
		document.removeEventListener('keydown', keydownFunc);
		el = document.getElementById(id);
		el.style.display = 'none';
		el.removeEventListener('click', clickFunc);
	}

	// pressing Esc button closes modal
	var keydownFunc = function(event) {
			if (event.key == "Escape")
				closeFunc(id);
		};
	document.addEventListener("keydown", keydownFunc);

	// click outside image panel or on button closes modal
	var clickFunc = function (e) {
			modalDiv = document.getElementById(id).children[0];
			inside = modalDiv.contains(e.target);
			onButton = modalDiv.children[0].contains(e.target);
			if (onButton || !inside)
				closeFunc(id);
		};
	el = document.getElementById(id);
	el.addEventListener('click', clickFunc);

	// show modal
	el.style.display = 'block';
}


// add the initially hidden modal frame for the TOC
{
	var div = document.createElement("div");
	div.setAttribute("id", "tocModal");
	div.innerHTML = '<div><i role="button" aria-label="Close popup"></i><iframe src="nav.xhtml"></iframe></div>';
	document.body.appendChild(div);
}
