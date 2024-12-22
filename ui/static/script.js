document.addEventListener('DOMContentLoaded', function() {
    const menuIcon = document.querySelector('header nav .fa-bars');
    const themeIcon = document.querySelector('header nav .fa-circle-half-stroke');
    const aside = document.querySelector('aside');
    const main = document.querySelector('main');
    const body = document.querySelector('body');


    menuIcon.addEventListener('click', function() {
        aside.classList.toggle('open');
    });

    themeIcon.addEventListener('click', function() {
        document.documentElement.classList.toggle('dark');
    });

    main.addEventListener('click', function() {
        if(aside.classList.contains('open')){
            aside.classList.toggle('open');
        }
    });
});
