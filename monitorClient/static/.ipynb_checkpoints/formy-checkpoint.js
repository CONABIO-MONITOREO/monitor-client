document.getElementById('form').onsubmit = function() {
  var directories = document.getElementsByName('directory');
  var selectedDirectories = [];
  for (var i = 0; i < directories.length; i++) {
    if (directories[i].checked) {
      selectedDirectories.push(directories[i].value);
    }
  }
  document.getElementById('selectedDirectories').value = selectedDirectories;
};

document.getElementById('text3').onchange = function() {
    console.log("Changed");
}
