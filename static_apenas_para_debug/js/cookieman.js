function setDarkCookie(state) {
    /* states: false, true */
    document.cookie = 'darkmode=' + state + ';path=/;SameSite=Lax';
}

function getDarkCookie() {
  var cookies = decodeURIComponent(document.cookie).split(';');
  for(var i = 0; i<cookies.length; i++) {
    var c = cookies[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf('darkmode=') == 0) {
      return c.split('=')[1];
    }
  }
  return "none";
}
