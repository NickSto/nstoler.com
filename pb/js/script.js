/* 
	This script file is part of the Paralogy Browser application.
*/

// auto-fill example query in search box
function fillExample() {
	$('#query').attr('value', "glutamate synthase");
	return false;
}

/*
This reads the HTML5 custom data attribute "data-e-bar-width" from each hit and
sets the width of the E-value indicator bar accordingly, to give a visual meter
of the strength of each hit. The indicator bar consists of a single, styled
<div> element.
*/
$('.e_bars').each(function() {
	var barWidth = $( this ).attr("data-e-bar-width");
	$( this ).width( barWidth );
});

