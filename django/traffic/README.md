Traffic
=======

This is my site's system for logging visits and visitors.

This document is mainly for notes for myself on the design.

Data sources
----------------
Django affords me a nice, flexible way to closely monitor visits to my site, but because some of my site is static resources like html, css, javascript, and images, these are served by Nginx without Django seeing it. So if I want to capture visits to both static and dynamic pages, I need at least two entry points to the system:

- Django views
- Nginx logs
    - `watch_nginx.py` runs as a daemon and watches an Nginx access log with a custom format.
        - When a new access is logged, the script sees it (through `tail -f`) and records it.


Cookies
-------
The system relies on two cookies, one corresponding to the dynamic portion of the site, and one for the static portion. The first one is set by my Django code, and the second is set by Nginx on all requests, including static ones Django doesn't see. The combination of the two allows me to stitch together the two halves of the site and resolve which visits are by the same user.


Object model
------------
Disclaimer: The object model may seem a little odd, which is partially due to its legacy dating back to my site's days in Perl CGI on a shared hosting provider.

### Visit
The basic unit of the system. Records a single HTTP request, with information like the url, the referrer, and timestamp. It also records the cookies the client sent and the ones the server sent back.

### Visitor
This is an object storing client-specific information. A new Visitor is created for every unique combination of ip address, user agent, and the two main cookies. If a new HTTP request occurs with the same information as an existing Visitor, the Visit is linked with the existing Visitor. If it changed, a new Visitor is created.

The rules for when the cookie fields were set used to be complex. The `version` field can be used to tell whether the new or old rules were being used when the Visitor was created.

`version == 1`: The cookie field(s) would be set on the client's first visit, based on cookies the server created and sent back. Or, if the client sent the server cookies, these would be used. After I created the second (Nginx) cookie, it got especially complicated. If a client visited a static page and received an Nginx cookie, then later visited a dynamic page, sending the Nginx cookie and receiving a dynamic cookie, the server would go back and find the original Visitor that only had the Nginx cookie, fill in the dynamic cookie, and re-use the original (but edited) Visitor. Ugh.

`version == 2`: The cookies now only represent cookies that the client *sent*, in the request where the Visitor was created. They are never pre-emptively set to a value the server made up and sent to the client, hoping it would accept it. It turns out, many clients (bots) don't accept cookies and keep visiting without returning ones you keep offering them. With the new rules, we never retroactively edit Visitors. If you want to know what cookies you sent to the client, that information is in the Visit object.

One issue with the Visitor object that's only become more important with the new cookie rules is the fact that the immutable Visitor identifiers (ip, user_agent, cookies) can change. A simple browser upgrade will change the user agent, creating a new Visitor. On a client's first visit, the created Visitor will have no cookies. On the very next request, the client sends our cookies back, creating a new Visitor with these cookies. I'd like a way to link Visitors which are clearly the same person. That's where the next level in the hierarchy comes in:

### User

This object is a later addition that aims to represent a real person. Its main use is to link Visitors with different identifying attributes but the same cookies. So when a person takes their laptop to a different ip address, the Visitor that will be created will be linked to the same User as their previous Visitor. The same happens in the above scenario where a client visits for the first time, sending no cookies, but then on the next request sends back the cookies the server just sent them. The administrator (hi) is also free to link up Visitors they know are the same person (e.g. Visitors for someone's laptop and phone browsers).

Issues
-------

One problem with the current object model arises from defining Visitors as immutable and unique for each combination of (ip, user_agent, cookies). The problem arises when multiple people with the same browser version share one IP address. On the first visit by Person A, their browser will send no cookies and create a Visitor identified only by ip address and user agent. Then, on the next request, the browser will return the cookies the server sent in reply to the first request. A new Visitor will be created with these cookies, and will be linked to the first Visitor by the same User. Then, if Person B visits for the first time, they will send the same ip address and user agent as the first person, and also no cookies. The same Visitor that was created for Person A's first visit will be used, and then on the next visit the new Visitor will also be linked to the first Visitor by the same User. From then on, through browser updates and ip address changes, these two people will continue to be identified as the same User.

I'm not sure how serious to consider this bug. It requires the somewhat unlikely scenario of two people with the same ip address and the exact same browser and version. But really all this requires is two people in the same house visiting my site at the same time in Chrome (Chrome is good about updating, meaning two people with Chrome will likely be on the same version at the same time). On the one hand my site isn't exactly super popular. But on the other hand, the way this scenario would actually happen is me showing my site to two people at once. Not so far-fetched.

Possible solutions include not making Visitors unique for the same (ip, user_agent, cookies) combination. Or, specifically, allowing creation of a new Visitor when the cookies are null and all I have is an ip and user agent. This doesn't sound too bad at first, but then that means if a bot that doesn't respect cookies (very common) keeps hitting my site, it will keep being assigned new Visitors and Users. Even though it'd be pretty easy to link all the visits by ip and user_agent, which would give a pretty low false positive rate.

Maybe the solution here is to stop trying to fit all this correlation into the object model. Instead, play the safe route and split Visitors who only share an ip and user_agent, then add tools to the Monitor so I can click and get a list of all visits from the same ip/user_agent combo.
