/*var FUTURE = new Date().getTime() + 5000;*/
var FUTURE = 1333141200000;
var MS_DAY =	24 * 60 * 60 * 1000;
var MS_HOUR =	60 * 60 * 1000;
var MS_MINUTE =	60 * 1000;
var MS_SECOND =	1000;
var changed = false;

updateTime();

setInterval('updateTime()', 200);

function updateTime() {
	
	if (changed === true) { return; }
	
	var now = new Date().getTime();
	var diff = FUTURE - now;
	
	if (diff <= 0 && changed === false) {
		changePage();
		changed = true;
	}
	
	var days = Math.floor(diff / MS_DAY);
	var remain = diff - (days * MS_DAY);
	var hours = Math.floor(remain / MS_HOUR);
	remain = remain - (hours * MS_HOUR);
	var minutes = Math.floor(remain / MS_MINUTE);
	remain = remain - (minutes * MS_MINUTE);
	var seconds = Math.floor(remain / MS_SECOND);
	
	if (hours < 10) {	hours = "0" + hours; }
	if (minutes < 10) {	minutes = "0" + minutes; }
	if (seconds < 10) {	seconds = "0" + seconds; }
	
	$('#days').html(days);
	$('#hours').html(hours);
	$('#minutes').html(minutes);
	$('#seconds').html(seconds);
	
}

function changePage() {
	$('#center').html(
			'<iframe width="640" height="480" src="http://www.youtube.com/embed/bDwV1VajmQQ?autoplay=1" frameborder="0" allowfullscreen></iframe> <div id="clock"><blink>00:00:00</blink></div>'
	);
	$('#center').css('left',-320);
	$('#center').css('top',-240);
	$('#center').css('width',640);
	$('#clock').css('font-size','200%');
	$('#clock').css('text-align','center');
}