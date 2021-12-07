darkbtn = document.getElementById('dark-mode');
darkbtn.addEventListener('click', function() {
    if (getDarkCookie() == 'false') {
        setDarkCookie(true);
        document.getElementById('theme-css').href = '/static/css/' + 'dark.css' + cssversion;
    } else {
        setDarkCookie(false);
        document.getElementById('theme-css').href = '/static/css/' + 'light.css' + cssversion;
    }
});