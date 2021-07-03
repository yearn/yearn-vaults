import requests

url = "https://raw.githubusercontent.com/yearn/brownie-wrapper-mix/master/contracts/AffiliateToken.sol"
r = requests.get(url, allow_redirects=True)

open("contracts/test/AffiliateToken.sol", "w").write(
    r.text.replace("@yearnvaults/contracts", "..")
)
