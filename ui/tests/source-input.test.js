import assert from 'node:assert/strict';
import test from 'node:test';
import {repositoryInputError} from '../dist/source-input.js';

test('repository source input protects the loopback request from URL credentials',()=>{
 assert.equal(repositoryInputError('/work/repository'),null);
 assert.equal(repositoryInputError(' https://azure.example.test/tfs/team/project/_git/repository '),null);
 assert.equal(repositoryInputError('https://user:token@azure.example.test/tfs/team/project/_git/repository'),'Do not put credentials in the URL.');
 assert.equal(repositoryInputError('ssh://azure.example.test/repository'),'Use an HTTPS Git clone URL.');
 assert.equal(repositoryInputError('https://azure.example.test/repository?token=secret'),'The clone URL must not include a query or fragment.');
});
