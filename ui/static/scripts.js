document.addEventListener('DOMContentLoaded', function () {
    const menuIcon = document.querySelector('header nav .fa-bars');
    const themeIcon = document.querySelector('header nav .fa-circle-half-stroke');
    const aside = document.querySelector('aside');
    const main = document.querySelector('main');
    const searchFields = document.querySelectorAll('input[type="search"]');
    let dataList = document.querySelector("datalist")

    let currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? "dark" : "light");
    localStorage.setItem("theme", currentTheme)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        currentTheme = event.matches ? "dark" : "light";
        localStorage.setItem(themeIcon, currentTheme)
    });
    document.documentElement.setAttribute('data-theme', currentTheme);


    menuIcon.addEventListener('click', function () {
        aside.classList.toggle('open');
    });

    themeIcon.addEventListener('click', function () {
        if (currentTheme == "light") {
            currentTheme = "dark"
        }
        else currentTheme = "light"

        localStorage.setItem("theme", currentTheme)
        document.documentElement.setAttribute('data-theme', currentTheme);
    });


    main.addEventListener('click', function () {
        if (aside.classList.contains('open')) {
            aside.classList.toggle('open');
        }
    });

    searchFields.forEach(field => {
        field.addEventListener('input', async function () {
            const query = field.value.trim();
            if (query.length < 2) {
                dataList.innerHTML = "";
                return;
            }
            try {
                const response = await fetch(`http://localhost:8080/autocomplete?q=${encodeURIComponent(query)}`);
                const suggestions = await response.json();

                dataList.innerHTML = "";
                suggestions.forEach(suggestion => {
                    const option = document.createElement("option");
                    option.value = suggestion;
                    dataList.appendChild(option);
                });
            } catch (error) {
                console.error("Error fetching autocomplete suggestions:", error);
            }
            field.focus();
        });
    });
});

function applySettings() {
    let indexType = document.getElementById("indexType").value;
    let spellCheck = document.getElementById("spellCheck").checked ? "true" : "false";
    let summaryType = document.getElementById("summaryType").value;
    let resultsPerPage = document.getElementById("resultsPerPage").value;

    let urlParams = new URLSearchParams(window.location.search);
    urlParams.set("index", indexType);
    urlParams.set("spellcheck", spellCheck);
    urlParams.set("summary_type", summaryType);
    urlParams.set("limit", resultsPerPage);

    window.location.search = urlParams.toString();
}
