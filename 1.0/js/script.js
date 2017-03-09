/* Author: 

*/

$(document).ready( function() {
	var linkElement = document.getElementById("nom")
	var link = linkElement.getAttribute("href");
	linkElement.setAttribute("href", link + "?l=2&r=" + document.referrer);
});