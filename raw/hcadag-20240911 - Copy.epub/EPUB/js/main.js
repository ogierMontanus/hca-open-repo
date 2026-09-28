/*
Main script for additions to an EPUB3 xhtml page.
Note: Since there are thousands of pages, we save space by adding common features through JavaScript.
Notably a facsimile is added to each xhtml page. The facsimiles reside on an external web server. 

Vanilla JavaScript
Author: Bo Krantz Simonsen, 2024, boks@kb.dk
License:  CC0 (public domain) except for the tlite library below
*/
//---------------------------------------

/* INCLUDE
tlite Tooltip library
Ref: https://github.com/chrisdavies/tlite
License MIT
Copyright (c) 2015 Chris Davies

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/
// boks@kb.dk: timer value 150 changed to 1300
function tlite(t){document.addEventListener("mouseover",function(e){var i=e.target,n=t(i);n||(n=(i=i.parentElement)&&t(i)),n&&tlite.show(i,n,!0)})}tlite.show=function(t,e,i){var n="data-tlite";e=e||{},(t.tooltip||function(t,e){function o(){tlite.hide(t,!0)}function l(){r||(r=function(t,e,i){function n(){o.className="tlite tlite-"+r+s;var e=t.offsetTop,i=t.offsetLeft;o.offsetParent===t&&(e=i=0);var n=t.offsetWidth,l=t.offsetHeight,d=o.offsetHeight,f=o.offsetWidth,a=i+n/2;o.style.top=("s"===r?e-d-10:"n"===r?e+l+10:e+l/2-d/2)+"px",o.style.left=("w"===s?i:"e"===s?i+n-f:"w"===r?i+n+10:"e"===r?i-f-10:a-f/2)+"px"}var o=document.createElement("span"),l=i.grav||t.getAttribute("data-tlite")||"n";o.innerHTML=e,t.appendChild(o);var r=l[0]||"",s=l[1]||"";n();var d=o.getBoundingClientRect();return"s"===r&&d.top<0?(r="n",n()):"n"===r&&d.bottom>window.innerHeight?(r="s",n()):"e"===r&&d.left<0?(r="w",n()):"w"===r&&d.right>window.innerWidth&&(r="e",n()),o.className+=" tlite-visible",o}(t,d,e))}var r,s,d;return t.addEventListener("mousedown",o),t.addEventListener("mouseleave",o),t.tooltip={show:function(){d=t.title||t.getAttribute(n)||d,t.title="",t.setAttribute(n,""),d&&!s&&(s=setTimeout(l,i?1300:1))},hide:function(t){if(i===t){s=clearTimeout(s);var e=r&&r.parentNode;e&&e.removeChild(r),r=void 0}}}}(t,e)).show()},tlite.hide=function(t,e){t.tooltip&&t.tooltip.hide(e)},"undefined"!=typeof module&&module.exports&&(module.exports=tlite);
// end tlite.min.js

//---------------------------------------

// the max number of pages in the various books (volumes)
const booksMaxPages = {
	 1: [40, 511], // [max roman numeral pages (e.g. XL), max arabic numeral pages]
	 2: [28, 488],
	 3: [24, 428],
	 4: [31, 476],
	 5: [20, 456],
	 6: [12, 353],
	 7: [15, 398],
	 8: [15, 464],
	 9: [12, 397],
	10: [15, 482]
}

var bookNb = 0;


//----- Facsimile default 'off'.  'on' when set by session cookie -----
try {
	var cookie = getCookie('showFacs');
	if (cookie && cookie=="on")
		document.body.classList.add("facsOn");
} catch (e) {
}


//----- create top bar with logo and navigation -----

topBanner = document.createElement("header");
topBanner.setAttribute("id", "banner");

{
	newElem = document.createElement("div");
	newElem.setAttribute("id", "leftNav");
	newElem.innerHTML = '<a class="screen" href="https://www.kb.dk/" title="Gå til kb.dk" role="button"><img src="img/kb-logo-low-white.svg" alt="KB logo" /></a><img class="print" src="img/kb-logo-digital-black.svg" alt="KB logo" />';
	topBanner.appendChild(newElem);
}

// navigation bar
newNav = document.createElement("nav");

{
	// button previous
	newElem = document.createElement("div");
	newElem.classList.add('btn');
	newElem.title = "Gå til forrige side";
	newElem.setAttribute("role", "button");
	
	newLink = document.createElement("a");
	newLink.textContent = "<";
	obj = document.querySelector('link[rel="prev"]')
	if (obj)
		newLink.href = obj.href;
	newElem.appendChild(newLink);  // Add link to paragraph
	newNav.appendChild(newElem);
}

{
	// page number
	newElem = document.createElement("div");
	newElem.classList.add('page');

	newElem2 = document.createTextNode("Dagbog ");
	newElem.appendChild(newElem2);

	pageNb = "";
	main = document.querySelector('main[data-facs]')
	if (main) {
		facs = main.getAttribute('data-facs');  // e.g. hcadag01fm_039
		const matches = facs.match(/^hcadag(\d\d)((?:fm)?)_(\d{3})$/);
		bookNb = parseInt(matches[1]);
		pageNb = parseInt(matches[3]);
		if (matches[2] == "fm") {
			pageNb = intToRoman(pageNb);
		}
	}
	
	newElem4 = document.createElement("div");
	newElem4.setAttribute("style", "display:inline-block");
	newElem4.title = "Vælg en anden dagbog";
	newElem2 = document.createElement("select");
	newElem2.id = 'sel';

	for (i=1; i<=10; i++) {
		newElem3 = document.createElement("option");
		newElem3.value = i;
		if (i == bookNb)
			newElem3.setAttribute("selected","");
		newElem3.appendChild( document.createTextNode( i.toString() ) );
		newElem2.appendChild(newElem3);
	}
	newElem2.addEventListener("change", (ev) => {
			val = ev.target.value;
			if (val && val.length) {
				goToBook(val);
			}
		});
	newElem4.appendChild(newElem2);
	newElem.appendChild(newElem4);

	newElem2 = document.createTextNode(" side ");
	newElem.appendChild(newElem2);
	
	newElem4 = document.createElement("div");
	newElem4.setAttribute("style", "display:inline-block");
	newElem4.title = "Indtast sidetal: I, II, III ..., 1, 2, 3 ...";
	newElem2 = document.createElement("input");
	newElem2.id = 'in';
	newElem2.value = pageNb;
	newElem2.addEventListener("change", (ev) => {
			input = ev.target.value;
			if (input && input.length) {
				input = input.trim();
				if (!input.length)
					return;
				if (input.match(/^[IVXLCDM]+$/i)) {
					// go to front matter page
					goToPage( romanToInt(input), true );
				} else if (input.match(/^[0-9]+$/)) {
					// go to main page
					goToPage( input, false );
				} else {
					alert("Indtast kun romertal eller arabertal");
				}
			}
		});
	newElem4.appendChild(newElem2);
	newElem.appendChild(newElem4);
	newNav.appendChild(newElem);
}

{
	// button next
	newElem = document.createElement("div");
	newElem.classList.add('btn');
	newElem.title = "Gå til næste side";
	newElem.setAttribute("role", "button");

	newLink = document.createElement("a");
	newLink.textContent = ">";
	obj = document.querySelector('link[rel="next"]')
	if (obj)
		newLink.href = obj.href;
	newElem.appendChild(newLink);  // Add link to paragraph
	newNav.appendChild(newElem);
}

{
	newElem = document.createElement("div");
	newElem.setAttribute("id", "rightNav");

	// facsimile is off link
	newLink = document.createElement("a");
	newLink.href = "javascript:facsOnOff(this,1)";
	newLink.setAttribute("role", "button");
	newLink.title = "Vis faksimile";
	newLink.innerHTML = '<img class="on" src="img/cameraOff-icon-white.svg" alt="Vis faksimile" />';
	newElem.appendChild(newLink);

	// facsimile is on link
	newLink = document.createElement("a");
	newLink.href = "javascript:facsOnOff(this,0)";
	newLink.setAttribute("role", "button");
	newLink.title = "Skjul faksimile";
	newLink.innerHTML = '<img class="off" src="img/cameraOn-icon-white.svg" alt="Skjul faksimile" />';
	newElem.appendChild(newLink);

	// open TOC
	newLink = document.createElement("a");
	newLink.href = "javascript:toc()";
	newLink.setAttribute("role", "button");
	newLink.title = "Indhold";
	newLink.innerHTML = '<img src="img/list-icon-white.svg" alt="Indhold" />';
	newElem.appendChild(newLink);
	topBanner.appendChild(newElem);
}

topBanner.appendChild(newNav);
document.body.appendChild(topBanner);

//----- add facsimile to table framework
{
	src = "";
	obj = document.querySelector('main')
	isSrcMissing = false;
	if (obj) {
		src = obj.getAttribute("data-facs");
		if (src) {
			volume = src.replace(/^hcadag(\d\d).*$/, '$1');
			src = volume + "/gif/" + src + ".gif";
		} else {
			src = "img/noFacsDefined.svg";
			// remove OCR top alignment
			obj.setAttribute('class', 'noFacsAlign');
			isSrcMissing = true;
		}
	}

	// create right column with facs
	obj = document.querySelector('main');
	if (obj && obj.parentNode && obj.parentNode.parentNode) {
		newElem = document.createElement("td");
		innerHTM = '<img class="facs lazy';
		if (isSrcMissing)
			innerHTM += ' missing';
		// prepare for loading only when it the element becomes visible
		innerHTM += '" alt="Faksimile" src="img/wdot.png" data-src="' + src + '"';
		if (!isSrcMissing)
			innerHTM += ' onerror="facsError(this)"';
		newElem.innerHTML = innerHTM + ' decoding="async" />';

		obj.parentNode.parentNode.appendChild(newElem);
	}
}

// add fixed image labels
{
	newElem = document.createElement("div");
	newElem.setAttribute("id", "ocrLabel");
	newElem.innerHTML = '<img src="img/ocr.svg" alt="Vertical OCR label" title="Vertical OCR label" />';
	document.body.appendChild(newElem);
	
	newElem = document.createElement("div");
	newElem.setAttribute("id", "facsLabel");
	newElem.innerHTML = '<img src="img/faksimile.svg" alt="Vertical faksimile label" title="Vertical faksimile label" />';
	document.body.appendChild(newElem);
}

// add an initially hidden modal frame for the TOC
{
	var div = document.createElement("div");
	div.setAttribute("id", "tocModal");
	div.innerHTML = '<div><i role="button" aria-label="Close popup"></i><iframe src="nav.xhtml"></iframe></div>';
	document.body.appendChild(div);
}

// activate tlite tooltips, position "North-East"
tlite( el => el.hasAttribute('title') && {grav: 'ne'} );


//------------------


function facsOnOff(imgElem, setOn) {
	if (setOn)
		document.body.classList.add("facsOn");
	else
		document.body.classList.remove("facsOn");

	// A cookie for this session only (exempt from GDPR requirements!)
	// it might not work in some EPUB readers, it works in web browsers accessing a web server (not using file://)
	setCookie('showFacs', setOn ? 'on' : 'off', null);
}

function facsError(imgElem) {
	imgElem.src = "img/noFacsFetched.svg";
	imgElem.classList.add("missing");
}


function goToBook(gotoBookNb) {
	if (!gotoBookNb)
		return;

	// first page in the book
	file = "hcadag" + gotoBookNb.padStart(2, '0') + "_001_I.xhtml";
	document.location.href = file;
}


function goToPage(pageNb, isFrontMatter) {
	if (!bookNb)
		return;
	pageNb = parseInt(pageNb);
	
	if (!pageNb) {
		// illegal, go to book's first page
		pageNb = 1;
		isFrontMatter = true;
	}

	// build filename
	file = "hcadag" + bookNb.toString().padStart(2, '0') + "_";
	if (isFrontMatter) {
		if (pageNb > booksMaxPages[bookNb][0])
			// too high: adjust to max.
			pageNb = booksMaxPages[bookNb][0];
		file += pageNb.toString().padStart(3, '0') + "_" + intToRoman(pageNb);
	} else {
		if (pageNb > booksMaxPages[bookNb][1])
			// too high: adjust to max.
			pageNb = booksMaxPages[bookNb][1];
		firstNb = booksMaxPages[bookNb][0] + pageNb;
		file += firstNb.toString().padStart(3, '0') + "_" + pageNb;
	}
	file += ".xhtml";
	document.location.href = file;
}


function intToRoman(num) {
	if (isNaN(num))
		return NaN;
	var digits = String(+num).split("");
	const key = ["","C","CC","CCC","CD","D","DC","DCC","DCCC","CM",
		   "","X","XX","XXX","XL","L","LX","LXX","LXXX","XC",
		   "","I","II","III","IV","V","VI","VII","VIII","IX"];
	var roman = "";
	var i = 3;
	while (i--)
		roman = (key[+digits.pop() + (i * 10)] || "") + roman;
	return Array(+digits.join("") + 1).join("M") + roman;
}


function romanToInt(roman) {
	roman = roman.toUpperCase();
	const romanList = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
	result = 0;
	for (i = 0; i < roman.length; i++) {
		num = romanList[roman[i]];
		nextNum = romanList[roman[i + 1]];
		if (nextNum && num < nextNum)
			result -= num;
		else
			result += num;
	}
	return result;
}


function getCookie(name) {
	var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
	return v ? v[2] : null;
}


function setCookie(name, value, days) {
	expires = '';
	if (days) {
		var d = new Date;
		d.setTime(d.getTime() + 24*60*60*1000*days);
		expires = ";expires=" + d.toGMTString();
	}
	document.cookie = name + "=" + value + ";path=/" + expires;
}


document.addEventListener("DOMContentLoaded", function() {
	// only lazy load images if visible
	var lazyImages = [].slice.call(document.querySelectorAll("img.lazy"));

	if ("IntersectionObserver" in window) {
		// Do this only if IntersectionObserver is supported
		// Create new observer object
		let lazyImageObserver = new IntersectionObserver(function(entries, observer) {
			// Loop through IntersectionObserverEntry objects
			entries.forEach(function(entry) {
				if (entry.isIntersecting) {
					// Do these if the target intersects with the root
					let lazyImage = entry.target;
					src = lazyImage.dataset.src;
					if (!src.startsWith('img/'))
						src = "https://img.kb.dk/ha/hcadag/hcadag_" + src;
					lazyImage.src = src;
					lazyImage.classList.remove("lazy");
					lazyImageObserver.unobserve(lazyImage);
				}
			});
		});

		// Loop through and observe each image
		lazyImages.forEach(function(lazyImage) {
			lazyImageObserver.observe(lazyImage);
		});
	} else {
		var lazyImages = document.getElementsByClassName("lazy");
		// https://stackoverflow.com/questions/3871547/js-iterating-over-result-of-getelementsbyclassname-using-array-foreach
		[].forEach.call(lazyImages, function (lazyImage) {
			lazyImage.src = lazyImage.dataset.src;
			lazyImage.classList.remove("lazy");
		});
	}

	// Current page typically opened from a link in illus.xhtml
	if (location.hash == '#illus' && document.getElementById('illusModal'))
		showIllus();
});


function toc() {
	showModal('tocModal');
}

function showIllus() {
	showModal('illusModal');
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
