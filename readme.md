# Poor's Man Mouser component finder

Using Mouser's API, I wrote these scripts for searching components using parameters. 
Mouser (as many other distributors) only allow to get som data, so this scripts only analizes the Descrption of the retrieved components, which is no ideal because sometimes descrpctions are wrong, or the script filters out valid components, etc. 

This is just a proof of concept and still needs a lot of work. 

## Usage

```
python poc.py
```

## Using Mouser API
- login/create an account
- create an mouser API application. Fill the form, and get teh API key.
  - Account details -> API ...

## Mouser API limitation

 Please read the limitations of the API [here](https://www.mouser.dk/api-search/)
 
 Basically you have a given number or request per minute and a total per day.

## References
- [Search API](https://api.mouser.com/api/docs/ui/index)
